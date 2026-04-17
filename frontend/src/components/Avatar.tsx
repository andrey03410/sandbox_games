export interface AvatarPreset {
  code: string
  label: string
  from: string
  to: string
  path: string
}

export const AVATARS: AvatarPreset[] = [
  {
    code: 'nebula',
    label: 'Туманность',
    from: '#667eea',
    to: '#764ba2',
    path: 'M12 2l2.5 7h7l-5.7 4.2 2.2 7.3L12 16.3 6 20.5l2.2-7.3L2.5 9h7z',
  },
  {
    code: 'flame',
    label: 'Пламя',
    from: '#f5576c',
    to: '#f093fb',
    path: 'M13.5 2c0 3 2 5 2 8 1 0 2-1 2-1 0 1 1 2 1 4a6.5 6.5 0 11-13 0c0-6 6-7 6-11z',
  },
  {
    code: 'leaf',
    label: 'Лист',
    from: '#43e97b',
    to: '#38f9d7',
    path: 'M4 20c0-9 7-16 16-16 0 9-7 16-16 16zm3-3c0-6 5-11 11-11',
  },
  {
    code: 'wave',
    label: 'Волна',
    from: '#4facfe',
    to: '#00f2fe',
    path: 'M2 13c2.5-3 5-3 7.5 0s5 3 7.5 0 4-2 5-1v8H2zm0-5c2.5-3 5-3 7.5 0s5 3 7.5 0 4-2 5-1',
  },
  {
    code: 'crown',
    label: 'Корона',
    from: '#fa709a',
    to: '#fee140',
    path: 'M4 18h16v2H4zM4 7l4 4 4-8 4 8 4-4-2 10H6z',
  },
  {
    code: 'moon',
    label: 'Луна',
    from: '#a8edea',
    to: '#fed6e3',
    path: 'M21 12.5A8.5 8.5 0 1111.5 4 6.5 6.5 0 0021 12.5z',
  },
]

export function getAvatar(code: string): AvatarPreset {
  return AVATARS.find((a) => a.code === code) ?? AVATARS[0]
}

export function Avatar({
  code,
  size = 40,
  ringed = false,
}: {
  code: string
  size?: number
  ringed?: boolean
}) {
  const a = getAvatar(code)
  const gradId = `grad-${a.code}`
  const usesStroke = a.code === 'leaf' || a.code === 'wave'
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      className={`avatar ${ringed ? 'avatar-ringed' : ''}`}
      aria-label={a.label}
    >
      <defs>
        <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor={a.from} />
          <stop offset="100%" stopColor={a.to} />
        </linearGradient>
      </defs>
      <circle cx="12" cy="12" r="11" fill={`url(#${gradId})`} />
      <path
        d={a.path}
        fill={usesStroke ? 'none' : 'rgba(255,255,255,0.92)'}
        stroke={usesStroke ? 'rgba(255,255,255,0.92)' : 'none'}
        strokeWidth={usesStroke ? 1.6 : 0}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  )
}
