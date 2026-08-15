// Publieke unsubscribe-pagina: werkt zonder login, one-click (RFC 8058 via POST-route).
import { verifyUnsubscribeToken } from '@/core/unsubscribe';
import { suppress } from '@/core/suppression';

export const dynamic = 'force-dynamic';

export default async function AfmeldenPage({ params }: { params: { token: string } }) {
  const data = verifyUnsubscribeToken(decodeURIComponent(params.token));
  let ok = false;
  if (data) {
    await suppress(data.tenantId, data.email, 'UNSUBSCRIBE');
    ok = true;
  }
  return (
    <main className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md rounded-xl border border-gray-200 bg-white p-8 text-center shadow-sm">
        {ok ? (
          <>
            <div className="mb-3 text-3xl">✓</div>
            <h1 className="mb-2 text-lg font-semibold">U bent afgemeld</h1>
            <p className="text-sm text-gray-600">
              U ontvangt geen e-mails meer van ons. Dit is direct verwerkt — er is geen verdere actie nodig.
            </p>
          </>
        ) : (
          <>
            <h1 className="mb-2 text-lg font-semibold">Ongeldige afmeldlink</h1>
            <p className="text-sm text-gray-600">Deze link is niet (meer) geldig. Beantwoord de ontvangen e-mail om u af te melden.</p>
          </>
        )}
      </div>
    </main>
  );
}
