import { redirect } from 'next/navigation';
import { headers } from 'next/headers';
import { prisma } from '@/lib/db';
import { verifyPassword, createSession, rateLimit, getSession } from '@/lib/auth';
import { Button, Input, Card } from '@/components/ui';

async function login(formData: FormData) {
  'use server';
  const email = String(formData.get('email') || '').trim().toLowerCase();
  const password = String(formData.get('password') || '');
  const ip = headers().get('x-forwarded-for') || 'local';
  if (!rateLimit(`login:${ip}`, 10, 15 * 60_000)) {
    redirect('/login?error=rate');
  }
  const user = await prisma.user.findUnique({ where: { email } });
  if (!user || !(await verifyPassword(password, user.passwordHash))) {
    redirect('/login?error=1');
  }
  await prisma.user.update({ where: { id: user.id }, data: { lastLoginAt: new Date() } });
  await createSession({
    userId: user.id,
    tenantId: user.tenantId,
    role: user.role,
    name: user.name,
    email: user.email,
  });
  redirect(user.role === 'CLIENT' ? '/portaal' : '/beheer');
}

export default async function LoginPage({ searchParams }: { searchParams: { error?: string } }) {
  const session = await getSession();
  if (session) redirect(session.role === 'CLIENT' ? '/portaal' : '/beheer');
  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <h1 className="mb-6 text-center text-2xl font-bold">
          LINK<span className="text-brand-600">.</span> Outreach
        </h1>
        <Card>
          <form action={login} className="space-y-4">
            {searchParams.error === 'rate' && (
              <p className="text-sm text-red-600">Te veel pogingen. Probeer het over 15 minuten opnieuw.</p>
            )}
            {searchParams.error === '1' && <p className="text-sm text-red-600">Onjuiste inloggegevens.</p>}
            <div>
              <label className="mb-1 block text-sm font-medium">E-mailadres</label>
              <Input name="email" type="email" required autoComplete="email" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Wachtwoord</label>
              <Input name="password" type="password" required autoComplete="current-password" />
            </div>
            <Button type="submit">Inloggen</Button>
          </form>
        </Card>
      </div>
    </main>
  );
}
