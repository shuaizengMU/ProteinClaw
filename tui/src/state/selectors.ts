import { useSyncExternalStore } from "react"
import type { AppStore, AppState } from "./AppStateStore"

let _store: AppStore | null = null

export function setStore(store: AppStore) {
  _store = store
}

export function useAppState<T>(selector: (s: AppState) => T): T {
  if (!_store) throw new Error("AppStore not initialized — call setStore() before rendering")
  const store = _store
  return useSyncExternalStore(
    store.subscribe.bind(store),
    () => selector(store.getSnapshot()),
  )
}

export function useDispatch() {
  if (!_store) throw new Error("AppStore not initialized — call setStore() before rendering")
  return _store.dispatch.bind(_store)
}
