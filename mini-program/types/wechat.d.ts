declare const wx: {
  login(options: { success(result: { code: string }): void; fail(): void }): void
  request(options: any): void
  getStorageSync(key: string): any
  setStorageSync(key: string, value: any): void
  navigateTo(options: { url: string }): void
  reLaunch(options: { url: string }): void
  showToast(options: { title: string; icon?: string }): void
}
declare function App(options: any): void
declare function Page(options: any): void
declare function getApp<T = any>(): T
