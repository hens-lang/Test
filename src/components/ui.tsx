// Kleine, herbruikbare UI-bouwstenen in shadcn-stijl (strak, licht, zakelijk).
import type { ReactNode } from 'react';

export function Card({ title, children, className = '' }: { title?: string; children: ReactNode; className?: string }) {
  return (
    <div className={`rounded-xl border border-gray-200 bg-white shadow-sm ${className}`}>
      {title && <div className="border-b border-gray-100 px-5 py-3 text-sm font-semibold text-gray-700">{title}</div>}
      <div className="p-5">{children}</div>
    </div>
  );
}

export function StatTile({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm">
      <div className="text-sm text-gray-500">{label}</div>
      <div className="mt-1 text-2xl font-bold">{value}</div>
      {sub && <div className="mt-1 text-xs text-gray-400">{sub}</div>}
    </div>
  );
}

const badgeColors: Record<string, string> = {
  green: 'bg-green-100 text-green-800',
  orange: 'bg-orange-100 text-orange-800',
  red: 'bg-red-100 text-red-800',
  gray: 'bg-gray-100 text-gray-700',
  blue: 'bg-blue-100 text-blue-800',
};

export function Badge({ color = 'gray', children }: { color?: keyof typeof badgeColors; children: ReactNode }) {
  return <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${badgeColors[color]}`}>{children}</span>;
}

export function statusColor(status: string): keyof typeof badgeColors {
  const green = ['ACTIVE', 'VALID', 'ACTIVE', 'QUALIFIED', 'MEETING_BOOKED', 'COMPLETED', 'SENT'];
  const orange = ['WARMING', 'RISKY', 'PENDING', 'REVIEW', 'PENDING_APPROVAL', 'PENDING_PERSONALIZATION', 'PAUSED', 'TRIAL', 'PROPOSED', 'SUGGESTED', 'NOT_NOW', 'NEW'];
  const red = ['ERROR', 'BLOCKED', 'INVALID', 'BOUNCED', 'UNSUBSCRIBED', 'REJECTED', 'STOPPED', 'CANCELED', 'NEGATIVE'];
  if (green.includes(status)) return 'green';
  if (orange.includes(status)) return 'orange';
  if (red.includes(status)) return 'red';
  return 'gray';
}

export function Table({ headers, children }: { headers: string[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200 bg-white shadow-sm">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs uppercase tracking-wide text-gray-500">
            {headers.map((h) => (
              <th key={h} className="px-4 py-3">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">{children}</tbody>
      </table>
    </div>
  );
}

export function Button({ children, variant = 'primary', ...props }: { children: ReactNode; variant?: 'primary' | 'secondary' | 'danger' } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const styles = {
    primary: 'bg-brand-600 text-white hover:bg-brand-700',
    secondary: 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50',
    danger: 'bg-red-600 text-white hover:bg-red-700',
  };
  return (
    <button className={`rounded-lg px-4 py-2 text-sm font-medium transition ${styles[variant]}`} {...props}>
      {children}
    </button>
  );
}

export function Input(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
      {...props}
    />
  );
}

export function Textarea(props: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
      {...props}
    />
  );
}
