import { requireStaff } from '@/lib/auth';
import { Card, Button, Input, Textarea } from '@/components/ui';
import { importContacts } from '../../actions';

export const dynamic = 'force-dynamic';

export default async function ImportPage({ searchParams }: { searchParams: { tenantId?: string; result?: string; dry?: string } }) {
  await requireStaff();
  const tenantId = searchParams.tenantId || '';
  const result = searchParams.result ? JSON.parse(searchParams.result) : null;

  return (
    <div className="max-w-3xl space-y-6">
      <h1 className="text-xl font-bold">Prospects importeren</h1>
      {result && (
        <Card title={searchParams.dry ? 'Dry-run resultaat (nog niets geïmporteerd)' : 'Importresultaat'}>
          <ul className="space-y-1 text-sm">
            <li>Totaal rijen: {result.total}</li>
            <li>{searchParams.dry ? 'Importeerbaar' : 'Geïmporteerd'}: {result.imported}</li>
            <li>Bijgewerkt (dedup): {result.updated}</li>
            <li className="text-orange-600">Overgeslagen (suppressielijst): {result.suppressed}</li>
            {result.errors.length > 0 && (
              <li className="text-red-600">
                Fouten:
                <ul className="ml-4 list-disc">
                  {result.errors.map((e: { row: number; message: string }, i: number) => (
                    <li key={i}>Rij {e.row}: {e.message}</li>
                  ))}
                </ul>
              </li>
            )}
          </ul>
        </Card>
      )}
      <Card title="CSV plakken + kolommapping">
        <form action={importContacts} className="space-y-4">
          <input type="hidden" name="tenantId" value={tenantId} />
          <div>
            <label className="mb-1 block text-sm">CSV-inhoud (eerste rij = kolomnamen)</label>
            <Textarea name="csv" rows={8} required placeholder={'voornaam,achternaam,email,bedrijf,functie,stad,branche\nJan,Jansen,jan@bedrijf.nl,Bedrijf BV,Directeur,Utrecht,logistiek'} />
          </div>
          <p className="text-sm text-gray-500">Kolommapping: geef per veld de kolomnaam uit jouw bestand op.</p>
          <div className="grid grid-cols-4 gap-3">
            {[
              ['map_firstName', 'Voornaam', 'voornaam'],
              ['map_lastName', 'Achternaam', 'achternaam'],
              ['map_email', 'E-mail', 'email'],
              ['map_company', 'Bedrijf', 'bedrijf'],
              ['map_domain', 'Domein', 'domein'],
              ['map_title', 'Functie', 'functie'],
              ['map_city', 'Stad', 'stad'],
              ['map_industry', 'Branche', 'branche'],
            ].map(([name, label, dflt]) => (
              <div key={name}>
                <label className="mb-1 block text-xs">{label}</label>
                <Input name={name} defaultValue={dflt} />
              </div>
            ))}
          </div>
          <p className="text-xs text-gray-500">
            Dedupliceren gebeurt automatisch op e-mail en bedrijfsdomein; adressen op de suppressielijst worden nooit geïmporteerd als actief contact. Domein wordt afgeleid van het e-mailadres als de kolom ontbreekt.
          </p>
          <div className="flex gap-3">
            <Button type="submit" name="dryRun" value="1" variant="secondary">Dry-run (foutenrapport)</Button>
            <Button type="submit">Definitief importeren</Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
