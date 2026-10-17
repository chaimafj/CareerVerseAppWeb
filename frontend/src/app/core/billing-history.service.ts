import { Injectable } from '@angular/core';

export interface PaymentTransaction {
  id: number;
  amount: number;
  currency: string;
  created_at: string;
  paid_at: string;
  premium_until: string | null;
}

export interface PaymentHistory {
  user_id: number;
  saved_at: string;
  transactions: PaymentTransaction[];
}

@Injectable({providedIn: 'root'})
export class BillingHistoryService {
  private open(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      if (!globalThis.indexedDB) {
        reject(new Error('Offline payment history is unavailable in this browser.'));
        return;
      }
      let blocked = false;
      const request = indexedDB.open('careerverse-billing', 1);
      request.onupgradeneeded = () => request.result.createObjectStore('history', {keyPath: 'user_id'});
      request.onsuccess = () => {
        if (blocked) { request.result.close(); return; }
        request.result.onversionchange = () => request.result.close();
        resolve(request.result);
      };
      request.onerror = () => reject(request.error);
      request.onblocked = () => {
        blocked = true;
        reject(new Error('Close other CareerVerse tabs to enable offline payment history.'));
      };
    });
  }

  private async transaction<T>(mode: IDBTransactionMode, operation: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
    const database = await this.open();
    try {
      return await new Promise<T>((resolve, reject) => {
        const transaction = database.transaction('history', mode);
        const request = operation(transaction.objectStore('history'));
        transaction.oncomplete = () => resolve(request.result);
        transaction.onerror = () => reject(transaction.error ?? request.error);
        transaction.onabort = () => reject(transaction.error ?? new Error('Offline payment history could not be saved.'));
      });
    } finally { database.close(); }
  }

  async read(userId: number): Promise<PaymentHistory | undefined> {
    const value: unknown = await this.transaction('readonly', store => store.get(userId));
    if (value === undefined) return undefined;
    if (!this.validHistory(value, userId)) throw new Error('The offline payment history is invalid. Refresh it while online.');
    return value;
  }

  async save(userId: number, transactions: PaymentTransaction[]): Promise<void> {
    const history: PaymentHistory = {user_id: userId, saved_at: new Date().toISOString(), transactions};
    if (!this.validHistory(history, userId)) throw new Error('The payment history response is invalid.');
    await this.transaction('readwrite', store => store.put(history));
  }

  private validHistory(value: unknown, userId: number): value is PaymentHistory {
    if (typeof value !== 'object' || value === null || !('user_id' in value) || value.user_id !== userId
        || !('saved_at' in value) || typeof value.saved_at !== 'string' || !Number.isFinite(Date.parse(value.saved_at))
        || !('transactions' in value) || !Array.isArray(value.transactions)) return false;
    return value.transactions.every((item: unknown) => {
      if (typeof item !== 'object' || item === null) return false;
      return 'id' in item && Number.isSafeInteger(item.id) && 'amount' in item && Number.isSafeInteger(item.amount)
        && 'currency' in item && typeof item.currency === 'string' && /^[a-z]{3}$/.test(item.currency)
        && 'created_at' in item && typeof item.created_at === 'string' && Number.isFinite(Date.parse(item.created_at))
        && 'paid_at' in item && typeof item.paid_at === 'string' && Number.isFinite(Date.parse(item.paid_at))
        && 'premium_until' in item && (item.premium_until === null
          || typeof item.premium_until === 'string' && Number.isFinite(Date.parse(item.premium_until)));
    });
  }
}
