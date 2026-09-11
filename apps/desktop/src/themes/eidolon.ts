import type { DesktopTheme, DesktopThemeColors } from './types'

// First-party Eidolon identity. Both variants stay dark by design; existing
// saved skins and appearance preferences remain untouched.
const colors: DesktopThemeColors = {
  background: '#09070d', foreground: '#f4f0fa',
  card: '#100d16', cardForeground: '#f4f0fa',
  muted: '#15111d', mutedForeground: '#b6abc8',
  popover: '#1b1625', popoverForeground: '#f4f0fa',
  primary: '#b995ff', primaryForeground: '#130b22',
  secondary: '#211a2d', secondaryForeground: '#e3d8f3',
  accent: '#2c2040', accentForeground: '#f4f0fa',
  border: '#32283e', input: '#15111d', ring: '#b995ff',
  midground: '#b995ff', midgroundForeground: '#130b22', composerRing: '#b995ff',
  destructive: '#f296a5', destructiveForeground: '#21080e',
  sidebarBackground: '#060509', sidebarBorder: '#221b2e',
  userBubble: '#211a2d', userBubbleBorder: '#443354'
}
export const eidolonTheme: DesktopTheme = {
  name: 'eidolon', label: 'Eidolon', description: 'Deep black, violet surfaces and lilac focus',
  colors, darkColors: { ...colors }
}
