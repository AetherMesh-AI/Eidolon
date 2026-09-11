/** Preserve every explicit route, especially canonical profile-session links. */
export function organizationStartHash(hash: string): string {
  return hash || '#/home'
}
