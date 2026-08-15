import Link from 'next/link';
import { redirect } from 'next/navigation';
import { getSession } from '@/lib/auth';

const NAV = [
  { href: '/beheer', label: 'Monitoring' },
  { href: '/beheer/tenants', label: 'Klanten' },
  { href: '/beheer/prospects', label: 'Prospects' },
  { href: '/beheer/campagnes', label: 'Campagnes' },
  { href: '/beheer/review', label: 'Review' },
  { href: '/beheer/inbox', label: 'Inbox' },
  { href: '/beheer/referrals', label: 'Referrals' },
  { href: '/beheer/infra', label: 'Domeinen & mailboxen' },
  { href: '/beheer/beldata', label: 'Beldata & inzichten' },
  { href: '/beheer/bibliotheek', label: 'Bibliotheek' },
  { href: '/beheer/abonnementen', label: 'Abonnementen' },
];

export default async function BeheerLayout({ children }: { children: React.ReactNode }) {
  const session = await getSession();
  if (!session) redirect('/login');
  if (session.role === 'CLIENT') redirect('/portaal');

  return (
    <div className="flex min-h-screen">
      <aside className="w-56 shrink-0 border-r border-gray-200 bg-white">
        <div className="px-5 py-5 text-lg font-bold">
          LINK<span className="text-brand-600">.</span> Outreach
        </div>
        <nav className="space-y-0.5 px-2">
          {NAV.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block rounded-lg px-3 py-2 text-sm text-gray-700 hover:bg-gray-100"
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="mt-8 border-t border-gray-100 px-5 py-4 text-xs text-gray-500">
          <div className="mb-2">{session.name}</div>
          <form action="/logout" method="post">
            <button className="text-brand-600 hover:underline">Uitloggen</button>
          </form>
        </div>
      </aside>
      <main className="flex-1 p-8">{children}</main>
    </div>
  );
}
