export const API_URL = 'http://localhost:8000'

export interface ApiRequestOptions extends Omit<RequestInit, 'body'> {
  token?: string | null
  body?: unknown
}

export async function apiFetch<T = unknown>(
  path: string,
  opts: ApiRequestOptions = {},
): Promise<T> {
  const { token, body, headers, ...rest } = opts
  const h = new Headers(headers)
  if (token) h.set('Authorization', `Bearer ${token}`)
  let serialized: BodyInit | undefined
  if (body !== undefined) {
    if (typeof body === 'string' || body instanceof FormData) {
      serialized = body as BodyInit
    } else {
      serialized = JSON.stringify(body)
      if (!h.has('Content-Type')) h.set('Content-Type', 'application/json')
    }
  }
  const resp = await fetch(`${API_URL}${path}`, { ...rest, headers: h, body: serialized })
  if (!resp.ok) {
    let detail = ''
    try {
      const data = await resp.json()
      detail = data?.detail ?? JSON.stringify(data)
    } catch {
      detail = await resp.text()
    }
    throw new Error(detail || `HTTP ${resp.status}`)
  }
  if (resp.status === 204) return undefined as T
  return (await resp.json()) as T
}
