// Tenant-isolatie (§15): bewijs dat de data-access-laag tenantId afdwingt.
import { describe, it, expect } from 'vitest';
import { injectTenantScope, TENANT_SCOPED_MODELS } from '@/lib/tenancy';

describe('tenant-isolatie (§15)', () => {
  it('injecteert tenantId in elke read op tenant-gebonden modellen', () => {
    for (const model of TENANT_SCOPED_MODELS) {
      const args = injectTenantScope(model, 'findMany', { where: { name: 'x' } }, 'tenant-a');
      expect((args.where as Record<string, unknown>).tenantId).toBe('tenant-a');
    }
  });

  it('een query van tenant A kan nooit data van tenant B opvragen', () => {
    // Zelfs als de aanroeper expliciet een andere tenantId meegeeft, wint de sessie-tenant.
    const args = injectTenantScope('Contact', 'findMany', { where: { tenantId: 'tenant-b' } }, 'tenant-a');
    expect((args.where as Record<string, unknown>).tenantId).toBe('tenant-a');
  });

  it('injecteert tenantId bij create', () => {
    const args = injectTenantScope('Lead', 'create', { data: { replySnippet: 'x' } }, 'tenant-a');
    expect((args.data as Record<string, unknown>).tenantId).toBe('tenant-a');
  });

  it('scoped updates en deletes op tenantId', () => {
    const upd = injectTenantScope('Contact', 'updateMany', { where: { id: '1' }, data: {} }, 'tenant-a');
    expect((upd.where as Record<string, unknown>).tenantId).toBe('tenant-a');
    const del = injectTenantScope('Contact', 'deleteMany', { where: {} }, 'tenant-a');
    expect((del.where as Record<string, unknown>).tenantId).toBe('tenant-a');
  });

  it('laat niet-tenant-modellen (Plan, TemplateStat) ongemoeid', () => {
    const args = injectTenantScope('Plan', 'findMany', { where: {} }, 'tenant-a');
    expect((args.where as Record<string, unknown>).tenantId).toBeUndefined();
  });
});
