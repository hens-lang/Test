import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/auth';
import { prisma } from '@/lib/db';

export default async function PortaalLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session) redirect('/login');
  if (session.role !== 'CLIENT' || !session.tenantId) redirect('/beheer');

  const tenant = await prisma.tenant.findUnique({
    where: { id: session.tenantId },
    include: { subscriptions: { where: { status: { in: ['ACTIVE', 'TRIAL'] } }, include: { plan: true } } },
  });
  if (!tenant) redirect('/login');
  const isDataOnly = tenant.subscriptions[0]?.plan.type === 'DATA_ONLY';
  const brand = tenant.brandColor || '#1d4ed8';

  const nav = [
    { href: '/portaal', label: 'Overzicht' },
    ...(isDataOnly ? [] : [
      { href: '/portaal/leads', label: 'Leads' },
      { href: '/portaal/prospects', label: 'Prospects' },
      { href: '/portaal/inzichten', label: 'Inzichten' },
    ]),
    { href: '/portaal/databestand', label: 'Databestand' },
    { href: '/portaal/maandrapport', label: 'Maandrapport' },
  ];

  return (
    <div className="min-h-screen">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center gap-6 px-6 py-4">
          {tenant.logoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={tenant.logoUrl} alt={tenant.name} className="h-8" />
          ) : (
            <span className="text-lg font-bold" style={{ color: brand }}>{tenant.name}</span>
          )}
          <nav className="flex gap-4 text-sm">
            {nav.map((item) => (
              <Link key={item.href} href={item.href} className="text-gray-600 hover:text-gray-900">{item.label}</Link>
            ))}
          </nav>
          <form action="/logout" method="post" className="ml-auto">
            <button className="text-sm text-gray-500 hover:underline">Uitloggen</button>
          </form>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
    </div>
  );
}
