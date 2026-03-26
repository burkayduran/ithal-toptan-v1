export function calculateRemaining(current: number, target: number): number {
  return Math.max(0, target - current);
}

export function calculateProgress(current: number, target: number): number {
  if (target === 0) return 0;
  return Math.min(100, Math.round((current / target) * 100));
}
