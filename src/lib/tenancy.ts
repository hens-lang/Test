// Multi-tenancy-afdwinging in de data-access-laag.
//
// Alle tenant-gebonden lees/schrijf-operaties in request-handlers horen via
// `tenantDb(tenantId)` te lopen: een Prisma-extensie die op elk relevant model
// automatisch `tenantId` in where/data injecteert. Zo kan een vergeten
// where-clausule nooit data van een andere tenant lekken.
//
// Tenant-overstijgende onderdelen (TemplateStat, globale Suppression, warm-up,
// planner) draaien bewust buiten deze laag in worker-jobs, en mogen alléén
// geanonimiseerde/niet-herleidbare data verwerken (zie §12 en anonymize.ts).
import { Prisma, PrismaClient } from '@prisma/client';
import { prisma } from './db';

// Modellen met een direct tenantId-veld.
export const TENANT_SCOPED_MODELS = [
  'Company',
  'Contact',
  'SendingDomain',
  'Campaign',
  'Activity',
  'Lead',
  'Referral',
  'ReplyDraft',
  'DataHealthRun',
  'Message',
  'Subscription',
  'InsightSnapshot',
] as const;

type TenantScopedModel = (typeof TENANT_SCOPED_MODELS)[number];

function isScoped(model: string | undefined): model is TenantScopedModel {
  return !!model && (TENANT_SCOPED_MODELS as readonly string[]).includes(model);
}

const READ_OPS = ['findFirst', 'findFirstOrThrow', 'findMany', 'findUnique', 'findUniqueOrThrow', 'count', 'aggregate', 'groupBy'];
const WRITE_OPS = ['create', 'createMany', 'update', 'updateMany', 'upsert', 'delete', 'deleteMany'];

export function tenantDb(tenantId: string) {
  if (!tenantId) throw new Error('tenantDb vereist een tenantId');
  return prisma.$extends({
    query: {
      $allModels: {
        async $allOperations({ model, operation, args, query }) {
          if (!isScoped(model)) return query(args);
          const a = (args ?? {}) as Record<string, unknown>;

          if (READ_OPS.includes(operation)) {
            a.where = { ...((a.where as object) ?? {}), tenantId };
          } else if (WRITE_OPS.includes(operation)) {
            if (operation === 'create') {
              a.data = { ...((a.data as object) ?? {}), tenantId };
            } else if (operation === 'createMany') {
              const data = a.data as Record<string, unknown>[] | Record<string, unknown>;
              a.data = Array.isArray(data)
                ? data.map((d) => ({ ...d, tenantId }))
                : { ...data, tenantId };
            } else if (operation === 'upsert') {
              a.where = { ...((a.where as object) ?? {}), tenantId };
              a.create = { ...((a.create as object) ?? {}), tenantId };
            } else {
              // update/updateMany/delete/deleteMany: scope op where; tenantId nooit muteren.
              a.where = { ...((a.where as object) ?? {}), tenantId };
              if (a.data && typeof a.data === 'object') {
                delete (a.data as Record<string, unknown>).tenantId;
              }
            }
          }
          return query(a as never);
        },
      },
    },
  });
}

export type TenantDb = ReturnType<typeof tenantDb>;

// Pure helper zodat de injectielogica ook zonder database unit-testbaar is.
export function injectTenantScope(
  model: string,
  operation: string,
  args: Record<string, unknown>,
  tenantId: string,
): Record<string, unknown> {
  if (!isScoped(model)) return args;
  const a = { ...args };
  if (READ_OPS.includes(operation)) {
    a.where = { ...((a.where as object) ?? {}), tenantId };
  } else if (operation === 'create') {
    a.data = { ...((a.data as object) ?? {}), tenantId };
  } else if (WRITE_OPS.includes(operation)) {
    a.where = { ...((a.where as object) ?? {}), tenantId };
  }
  return a;
}
