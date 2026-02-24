/**
 * Roles constant - matches backend allowed roles
 */

export const BASE_ROLES = [
  { value: 'admin', label: 'Διαχειριστής' },
  { value: 'waiter', label: 'Σερβιτόρος' },
];

export const ROLE_LABELS = {
  admin: 'Διαχειριστής',
  waiter: 'Σερβιτόρος',
};

export function buildStationRoles(workstations = []) {
  return workstations
    .filter((ws) => ws.slug && ws.slug !== 'waiter')
    .map((ws) => ({
      value: `station_${ws.slug}`,
      label: `Σταθμός ${ws.name}`,
      stationSlug: ws.slug,
    }));
}

export function getRoleLabel(role, workstations = []) {
  if (ROLE_LABELS[role]) return ROLE_LABELS[role];
  if (typeof role === 'string' && role.startsWith('station_')) {
    const slug = role.replace('station_', '');
    const ws = workstations.find((item) => item.slug === slug);
    return ws?.name || slug;
  }
  return role;
}
