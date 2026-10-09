import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

class ApiService {}
class LocaleService {}
class ActivatedRoute {}
class Router {}
class AuthServiceToken {}
class HttpErrorResponse { constructor(status, error) { this.status=status; this.error=error; } }
const signal = initial => {
  let value=initial;
  const read=()=>value;
  read.set=next=>{value=next;};
  read.update=fn=>{value=fn(value);};
  return read;
};
function load(file, providers, globals={}) {
  const exports={};
  const require = name => {
    if(name==='@angular/core') return {inject:token=>providers.get(token),signal,computed:fn=>fn,Injectable:()=>target=>target,Component:()=>target=>target,Input:()=>()=>{}};
    if(name.endsWith('api.service')) return {ApiService,errorMessage:error=>error.message};
    if(name.endsWith('locale.service')) return {LocaleService,TranslatePipe:class{},LocalDatePipe:class{}};
    if(name==='@angular/router') return {ActivatedRoute,Router,RouterLink:class{}};
    if(name==='@angular/common') return {KeyValuePipe:class{},TitleCasePipe:class{}};
    if(name==='@angular/forms') return {FormsModule:class{}};
    if(name.endsWith('auth.service')) return {AuthService:AuthServiceToken};
    if(name==='@angular/common/http') return {HttpClient:class{},HttpErrorResponse};
    if(name==='rxjs') return {firstValueFrom:value=>value};
    if(name.endsWith('workshop-workspace.component')) return {WorkshopWorkspaceComponent:class{}};
    if(name.endsWith('career-assessment.component')) return {CareerAssessmentComponent:class{}};
    if(name.endsWith('app-icon.component')) return {AppIconComponent:class{}};
    if(name.endsWith('career-art.component')) return {CareerArtComponent:class{}};
    if(name.endsWith('google-signin.component')) return {GoogleSigninComponent:class{}};
    if(name==='@ionic/angular') return {IonicModule:class{}};
    throw new Error(`Unexpected test dependency: ${name}`);
  };
  const compiled=ts.transpileModule(readFileSync(file,'utf8'),{
    compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,experimentalDecorators:true},
  }).outputText;
  vm.runInNewContext(compiled,{exports,require,URL,console,...globals});
  return exports;
}
const calls=[];
let configured=true;
let permission='granted';
let permissionCalls=0;
let current=null;
let unsubscribeCalls=0;
let failSave=false;
let language='en';
const registration={pushManager:{
  getSubscription:async()=>current,
  subscribe:async()=>{current={
    endpoint:'https://fcm.googleapis.com/fcm/send/test',
    toJSON:()=>({endpoint:'https://fcm.googleapis.com/fcm/send/test',keys:{p256dh:'test',auth:'test'}}),
    unsubscribe:async()=>{current=null;unsubscribeCalls++;return true;},
  };return current;},
}};
const api={
  get:async()=>({configured,public_key:Buffer.alloc(65).toString('base64url')}),
  post:async(path,body)=>{calls.push({method:'POST',path,body});if(failSave)throw new Error('Subscription rejected');},
  delete:async(path,body)=>{calls.push({method:'DELETE',path,body});},
};
const providers=new Map([[ApiService,api],[LocaleService,{language:()=>language}]]);
const {PushService}=load('src/app/core/push.service.ts',providers,{
  navigator:{serviceWorker:{register:async()=>registration,ready:Promise.resolve(registration),getRegistration:async()=>registration}},
  window:{PushManager:class{},isSecureContext:true},
  Notification:{requestPermission:async()=>{permissionCalls++;return permission;}},
  atob:value=>Buffer.from(value,'base64').toString('binary'),
});
const push=new PushService();
configured=false;
await assert.rejects(()=>push.enable(),/not configured/);
assert.equal(permissionCalls,0);
configured=true;permission='denied';
await assert.rejects(()=>push.enable(),/permission/);
assert.equal(current,null);
permission='granted';failSave=true;
await assert.rejects(()=>push.enable(),/Subscription rejected/);
assert.equal(current,null);
assert.equal(unsubscribeCalls,1);
failSave=false;
await push.enable();
assert.equal(await push.enabled(),true);
assert.equal(calls.at(-1).body.language,'en');
failSave=true;
await assert.rejects(()=>push.enable(),/Subscription rejected/);
assert.equal(await push.enabled(),true,'Failed refresh must not silently unsubscribe an existing subscription');
failSave=false;language='ar';
await push.updateLanguage();
assert.equal(calls.at(-1).body.language,'ar');
await push.disable();
assert.equal(calls.at(-1).method,'DELETE');
assert.equal(await push.enabled(),false);

const redirects=[];
let checkoutUrl='https://evil.example/pay';
const billingApi={
  get:async()=>({configured:true,premium_until:null,is_premium:false}),
  post:async()=>({url:checkoutUrl}),
};
const {PremiumPage}=load('src/app/pages/premium.page.ts',new Map([
  [ApiService,billingApi],[ActivatedRoute,{snapshot:{queryParamMap:{get:()=>null}}}],
]),{window:{location:{assign:url=>redirects.push(url)}}});
const premium=new PremiumPage();
await premium.load();
await premium.checkout();
assert.equal(redirects.length,0);
assert.equal(premium.error(),'Invalid Stripe checkout URL.');
checkoutUrl='https://checkout.stripe.com/c/pay/test_session';
await premium.checkout();
assert.equal(redirects[0],checkoutUrl);
assert.equal(premium.status().is_premium,false,'Checkout must never grant Premium in the client');
premium.busy.set(false);
premium.status.set({configured:true,is_premium:true,premium_until:'2026-12-08T20:00:00Z'});
await premium.checkout();
assert.equal(redirects.length,1,'Active Premium must not start another checkout');

let scheduled;
let cleared=false;
let reads=0;
let active=false;
let failStatus=false;
const {PremiumPage:ReturnedPremium}=load('src/app/pages/premium.page.ts',new Map([
  [ApiService,{get:async()=>{reads++;if(failStatus)throw new Error('Status unavailable');return {configured:true,is_premium:active,premium_until:active?'2026-12-08T20:00:00Z':null};}}],
  [ActivatedRoute,{snapshot:{queryParamMap:{get:()=>'success'}}}],
]),{
  setTimeout:callback=>{scheduled=callback;return 1;},
  clearTimeout:()=>{scheduled=undefined;cleared=true;},
});
const returned=new ReturnedPremium();
await returned.load();
assert.equal(returned.status().is_premium,false);
assert.equal(returned.waiting(),true);
assert.ok(scheduled);
active=true;
await scheduled();
// Timer callbacks intentionally launch load without returning its promise.
await Promise.resolve();await Promise.resolve();
assert.equal(returned.status().is_premium,true);
assert.equal(returned.waiting(),false);
assert.equal(scheduled,undefined);
assert.equal(reads,2);
active=false;
const pending=new ReturnedPremium();
for(let i=0;i<10;i++)await pending.load();
assert.equal(pending.waiting(),false);
assert.equal(scheduled,undefined,'Polling must be bounded');
const disposed=new ReturnedPremium();
await disposed.load();
disposed.ngOnDestroy();
assert.equal(cleared,true);
assert.equal(scheduled,undefined);
failStatus=true;
const failed=new ReturnedPremium();
await failed.load();
assert.equal(failed.error(),'Status unavailable');
assert.equal(failed.waiting(),false);
console.log('Verified push permission/configuration, subscription failure cleanup, locale update, logout removal and safe test Checkout redirects.');

const {errorMessage: apiError}=load('src/app/core/api.service.ts',new Map());
assert.equal(apiError(new HttpErrorResponse(403,{code:'premium_required'})),
  'Active Premium access is required for this lab and its course.');
assert.match(apiError(new HttpErrorResponse(403,{})),/Sign in/);

const questions=[
  {id:1,multiple:false,options:[{id:11},{id:12}]},
  {id:2,multiple:true,options:[{id:21},{id:22}]},
];
let locked=true;
let failPreview=false;
let starts=0;
const submissions=[];
const navigations=[];
let timerCleared=false;
let listenerRemoved=false;
const {LabPage}=load('src/app/pages/lab.page.ts',new Map([
  [ApiService,{
    lab:async()=>{if(failPreview)throw new Error('Preview unavailable');return {id:10,locked,question_count:2};},
    startLab:async()=>{starts++;return {id:99,questions};},
    submit:async(id,answers)=>{submissions.push({id,answers});return {id:123};},
  }],
  [ActivatedRoute,{snapshot:{paramMap:{get:()=> '10'}}}],
  [Router,{navigate:async commands=>{navigations.push(commands);}}],
]),{
  window:{addEventListener:()=>{},removeEventListener:()=>{listenerRemoved=true;}},
  setInterval:()=>123,clearInterval:()=>{timerCleared=true;},
});
const lab=new LabPage();
await lab.load();
assert.equal(lab.detail().locked,true);
await lab.start();
assert.equal(starts,0,'Locked briefing must not start an attempt');
failPreview=true;
await lab.load();
assert.equal(lab.error(),'Preview unavailable');
failPreview=false;locked=false;
await lab.load();
await lab.start();
assert.equal(starts,1);
await lab.start();
assert.equal(starts,1,'An ongoing attempt must not be replaced');
lab.toggle(questions[0],11);
lab.toggle(questions[0],12);
assert.equal(lab.selected(1,11),false);
assert.equal(lab.selected(1,12),true);
await lab.submit();
assert.equal(submissions.length,0,'Incomplete answer sets must not submit');
lab.toggle(questions[1],21);
lab.toggle(questions[1],22);
assert.equal(lab.answeredCount(),2);
await lab.submit();
assert.equal(submissions[0].id,99);
assert.deepEqual(Array.from(submissions[0].answers[1].option_ids),[21,22]);
assert.deepEqual(Array.from(navigations[0]),['/results',123]);
assert.equal(lab.attempt(),null);
assert.equal(timerCleared,true);
lab.ngOnDestroy();
assert.equal(listenerRemoved,true);
console.log('Verified Premium error handling, locked briefings, answer review, complete submission and timer cleanup.');

const authPosts=[];
const {AuthService}=load('src/app/core/auth.service.ts',new Map([[ApiService,{
  csrf:async()=>{},
  post:async(path,body,headers)=>{authPosts.push({path,body,headers});return {id:1};},
}],[LocaleService,{language:()=> 'fr'}]]));
const auth=new AuthService();
await auth.authenticate('login',{email:'qa@example.test',password:'test-only',name:''});
assert.deepEqual(Object.keys(authPosts[0].body).sort(),['email','password']);
await auth.authenticate('register',{email:'qa@example.test',password:'test-only',name:'Student'});
assert.equal(authPosts[1].body.name,'Student');
assert.equal(authPosts[0].headers['Accept-Language'],'fr');
assert.equal(authPosts[1].headers['Accept-Language'],'fr');
await auth.authenticateGoogle('test-google-credential');
assert.equal(authPosts[2].path,'auth/google/');
assert.equal(authPosts[2].body.credential,'test-google-credential');
assert.equal(authPosts[2].headers['Accept-Language'],'fr');
console.log('Verified login excludes registration-only fields.');

let completionCalls=0;
const {CoursePage}=load('src/app/pages/course.page.ts',new Map([
  [ApiService,{
    course:async()=>({id:1,completed:false,lessons:[{title:'Lesson'}]}),
    completeCourse:async()=>{completionCalls++;},
  }],
  [ActivatedRoute,{snapshot:{paramMap:{get:()=> '1'}}}],
]));
const coursePage=new CoursePage();
await coursePage.load();
await coursePage.finish();
assert.equal(coursePage.course().completed,true);
await coursePage.finish();
assert.equal(completionCalls,1,'Completed course must not be submitted twice');
console.log('Verified course completion stays on the course without starting a lab.');

const {LearningCatalogPage}=load('src/app/pages/learning-catalog.page.ts',new Map([
  [ApiService,{}],[ActivatedRoute,{snapshot:{data:{catalog:'labs'}}}],
]));
const catalog=new LearningCatalogPage();
assert.equal(catalog.labGroups().length,0);
catalog.labs.set([
  {id:1,career_slug:'angular',career_title:'Angular Developer'},
  {id:2,career_slug:'cloud',career_title:'Cloud Engineer'},
  {id:3,career_slug:'angular',career_title:'Angular Developer',completed:true},
  {id:4,career_slug:'cloud',career_title:'Cloud Engineer',is_premium:true},
]);
assert.equal(catalog.labGroups().length,2);
assert.deepEqual(Array.from(catalog.labGroups()[0].items,lab=>lab.id),[1,3]);
assert.deepEqual(Array.from(catalog.labGroups()[1].items,lab=>lab.id),[2,4]);
assert.equal(catalog.labGroups()[0].items[1].completed,true);
assert.equal(catalog.labGroups()[1].items[1].is_premium,true);
console.log('Verified Labs grouping by career preserves order, completion and Premium metadata.');
assert.equal(catalog.courseGroups().length,0);
catalog.courses.set([
  {id:1,career_slug:'angular',career_title:'Angular Developer',completed:true},
  {id:2,career_slug:'cloud',career_title:'Cloud Engineer'},
  {id:3,career_slug:'angular',career_title:'Angular Developer',is_premium:true,locked:true},
]);
assert.equal(catalog.courseGroups().length,2);
assert.deepEqual(Array.from(catalog.courseGroups()[0].items,course=>course.id),[1,3]);
assert.equal(catalog.courseGroups()[0].items[0].completed,true);
assert.equal(catalog.courseGroups()[0].items[1].locked,true);
assert.equal(catalog.courseGroups()[1].title,'Cloud Engineer');
console.log('Verified Courses grouping by career preserves completion, order and locked Premium courses.');

const workshopSubmissions=[];
const codeQuestion={id:7,kind:'code',multiple:false,options:[],workspace:{before:'if (',after:') grant();'}};
const {LabPage:WorkshopLab}=load('src/app/pages/lab.page.ts',new Map([
  [ApiService,{
    lab:async()=>({id:10,locked:false,question_count:1}),
    startLab:async()=>({id:88,questions:[codeQuestion]}),
    submit:async(id,answers)=>{workshopSubmissions.push({id,answers});return {id:8};},
  }],
  [ActivatedRoute,{snapshot:{paramMap:{get:()=> '10'}}}],
  [Router,{navigate:async()=>{}}],
]),{window:{addEventListener:()=>{},removeEventListener:()=>{}},setInterval:()=>1,clearInterval:()=>{}});
const workshop=new WorkshopLab();
await workshop.load();await workshop.start();
assert.equal(workshop.hasCurrentAnswer(),false);
workshop.setCode(7,'   ');
assert.equal(workshop.allAnswered(),false);
workshop.setCode(7,'status.is_premium');
assert.equal(workshop.hasCurrentAnswer(),true);
assert.equal(workshop.answeredCount(),1);
await workshop.submit();
assert.equal(workshopSubmissions[0].answers[0].code_text,'status.is_premium');
assert.equal(workshopSubmissions[0].answers[0].option_ids.length,0);
console.log('Verified typed workshop answers, blank-input gating and server submission shape.');

let assessmentFails=false;
const finalAssessment={career_slug:'angular',complete:true,final_score:46.67,needs_improvement:true};
const {ResultPage}=load('src/app/pages/lab.page.ts',new Map([
  [ApiService,{
    result:async()=>({id:10,career_slug:'angular'}),
    assessment:async slug=>{assert.equal(slug,'angular');if(assessmentFails)throw new Error('Assessment unavailable');return finalAssessment;},
  }],
  [ActivatedRoute,{snapshot:{paramMap:{get:()=> '10'}}}],
]));
const resultsPage=new ResultPage();
await resultsPage.load();
assert.equal(resultsPage.assessment().final_score,46.67);
assert.equal(resultsPage.assessment().needs_improvement,true);
assessmentFails=true;
await resultsPage.load();
assert.equal(resultsPage.error(),'Assessment unavailable');
assert.equal(resultsPage.result().id,10,'Assessment failure must not hide saved corrections');
console.log('Verified current career assessment on results and explicit assessment failure feedback.');

let savedProfile={name:'Student',interests:['design']};
const {ProfilePage}=load('src/app/pages/profile.page.ts',new Map([
  [AuthServiceToken,{
    user:()=>savedProfile,
    saveProfile:async data=>{savedProfile={...savedProfile,...data};},
  }],
  [ApiService,{careers:async()=>[{interests:['design','programming']}]}],
]));
const profile=new ProfilePage();
profile.customInterest=' Robotics ';
assert.equal(profile.addInterest(),true);
profile.customInterest='ROBOTICS';
assert.equal(profile.addInterest(),true);
assert.equal(profile.interests.filter(value=>value==='robotics').length,1);
profile.customInterest='Astronomy';
await profile.save();
assert.deepEqual(Array.from(savedProfile.interests),['design','robotics','astronomy']);
assert.equal(profile.saved(),true);
await profile.loadInterests();
assert.equal(profile.choices().includes('robotics'),true);
profile.customInterest=' ';
assert.equal(profile.addInterest(),false);
profile.interests=Array.from({length:30},(_,i)=>`interest-${i}`);
profile.customInterest='another';
assert.equal(profile.addInterest(),false);
profile.toggle('programming');
assert.equal(profile.interests.length,30);
assert.equal(profile.interestError(),'You can select up to 30 interests.');
console.log('Verified custom interest normalization, pending save, catalogue merge and selection limits.');

let confirmDelete=false;
let deleteFailure=false;
const deletedNotifications=[];
let readFailure=false;
let completeRead;
const notificationReads=[];
const notificationRoutes=[];
const {NotificationsPage}=load('src/app/pages/notifications.page.ts',new Map([
  [ApiService,{
    get:async()=>[{id:1,read:false,path:'/careers'},{id:2,read:true,path:'/labs'}],
    delete:async path=>{if(deleteFailure)throw new Error('Delete failed');deletedNotifications.push(path);},
    post:async path=>{
      notificationReads.push(path);
      if(readFailure)throw new Error('Read failed');
      await new Promise(resolve=>{completeRead=resolve;});
    },
  }],
  [LocaleService,{t:value=>value}],
  [Router,{navigateByUrl:async path=>{notificationRoutes.push(path);return true;}}],
]),{window:{confirm:()=>confirmDelete}});
const inbox=new NotificationsPage();
await inbox.load();
assert.equal(inbox.unreadCount(),1);
inbox.unreadOnly.set(true);
assert.equal(inbox.visibleItems().length,1);
readFailure=true;
await inbox.explore(inbox.items()[0]);
assert.equal(inbox.items()[0].read,false);
assert.equal(inbox.error(),'Read failed');
assert.equal(notificationRoutes.length,0);
readFailure=false;
const opening=inbox.explore(inbox.items()[0]);
assert.equal(inbox.busy(),true);
assert.equal(inbox.items()[0].read,false);
assert.equal(notificationRoutes.length,0);
assert.equal(await inbox.read(inbox.items()[0]),false);
completeRead();
await opening;
assert.equal(inbox.items()[0].read,true);
assert.equal(inbox.unreadCount(),0);
assert.equal(inbox.visibleItems().length,0);
assert.equal(notificationRoutes[0],'/careers');
const readCount=notificationReads.length;
await inbox.explore(inbox.items()[0]);
assert.equal(notificationReads.length,readCount);
await inbox.load();
const marking=inbox.read(inbox.items()[0]);
completeRead();
assert.equal(await marking,true);
assert.equal(notificationRoutes.length,2);
assert.equal(inbox.items()[0].read,true);
await inbox.load();
await inbox.removeAll();
assert.equal(deletedNotifications.length,0);
confirmDelete=true;deleteFailure=true;
await inbox.removeAll();
assert.equal(inbox.items().length,2);
assert.equal(inbox.error(),'Delete failed');
deleteFailure=false;
inbox.busy.set(true);
await inbox.removeAll();
assert.equal(deletedNotifications.length,0);
inbox.busy.set(false);
await inbox.removeAll();
assert.equal(inbox.items().length,0);
assert.equal(inbox.unreadCount(),0);
assert.equal(inbox.notice(),'All notifications deleted.');
assert.equal(deletedNotifications[0],'notifications/');
await inbox.removeAll();
assert.equal(deletedNotifications.length,1);
console.log('Verified notification filtering, bulk deletion confirmation, failure preservation, busy/empty guards and removal of read/unread items.');
console.log('Verified notification read persistence before navigation, card read, busy guard, already-read reuse and failure without navigation.');

const {CareerArtComponent}=load('src/app/widgets/career-art.component.ts',new Map());
const art=new CareerArtComponent();
for(const [subject,variant] of [['angular-developer','code'],['cloud-engineer','cloud'],['cybersecurity-analyst','security'],['premium','premium'],['new-career','launch']]) {
  art.subject=subject;
  assert.equal(art.variant,variant);
}
assert.equal(art.animated,false);
const {AppIconComponent}=load('src/app/widgets/app-icon.component.ts',new Map());
const icon=new AppIconComponent();
for(const name of ['home','compass','book','lab','sparkles','user','bell','crown','shield','logout','sun','moon']) {
  icon.name=name;
  assert.ok(icon.path?.length>10,`Missing icon: ${name}`);
}
console.log('Verified original career illustration variants, static-by-default artwork and all navigation icon paths.');

const resetCalls=[];
let resetError=false;
let resetParams={};
const resetProviders=new Map([
  [ApiService,{csrf:async()=>{},post:async(path,body,headers)=>{
    resetCalls.push({path,body,headers});
    if(resetError)throw new Error('This reset link is invalid or expired. Request a new one.');
  }}],
  [LocaleService,{language:()=> 'ar'}],
  [AuthServiceToken,{user:signal({id:1})}],
  [ActivatedRoute,{snapshot:{paramMap:{get:key=>resetParams[key]??null}}}],
]);
const {PasswordResetPage}=load('src/app/pages/password-reset.page.ts',resetProviders);
const requestReset=new PasswordResetPage();
requestReset.email=' qa@example.test ';
await requestReset.submit();
assert.equal(resetCalls[0].path,'auth/password-reset/');
assert.equal(resetCalls[0].body.email,'qa@example.test');
assert.equal(resetCalls[0].headers['Accept-Language'],'ar');
assert.equal(requestReset.success(),true);
await requestReset.submit();
assert.equal(resetCalls.length,1);
resetParams={uid:'MQ',token:'test-token'};
const confirmReset=new PasswordResetPage();
confirmReset.password='New-932-passphrase!';confirmReset.confirm='Wrong';
await confirmReset.submit();
assert.equal(resetCalls.length,1);
assert.equal(confirmReset.error(),'The passwords do not match.');
confirmReset.confirm=confirmReset.password;resetError=true;
await confirmReset.submit();
assert.equal(confirmReset.success(),false);
assert.ok(confirmReset.error().includes('expired'));
resetError=false;
await confirmReset.submit();
assert.equal(confirmReset.success(),true);
assert.equal(confirmReset.password,'');
assert.equal(resetProviders.get(AuthServiceToken).user(),null);
assert.equal(resetCalls.at(-1).path,'auth/password-reset/confirm/');
assert.equal(resetCalls.at(-1).body.uid,'MQ');
console.log('Verified password reset request, localized headers, password mismatch, invalid-link feedback, success and session clearing.');
