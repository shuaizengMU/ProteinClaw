// Minimal stub for Anthropic-internal semver utility
import { gte as semverGte } from 'semver'

export function gte(v1: string, v2: string): boolean {
  return semverGte(v1, v2)
}
