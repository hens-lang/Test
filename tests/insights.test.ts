import { describe, it, expect } from 'vitest';
import { clusterObjection, aggregateObjections, titleGroup } from '@/core/objections';
import { computeSegments, writeConclusions, computeTrends } from '@/jobs/insights';

describe('bezwarenclustering (marktintelligentie)', () => {
  it('herkent de hoofdclusters', () => {
    expect(clusterObjection('We zijn al voorzien, vaste leverancier.')).toBe('AL_VOORZIEN');
    expect(clusterObjection('Ons budget is bevroren tot Q1.')).toBe('GEEN_BUDGET');
    expect(clusterObjection('Niet op dit moment, kom in het najaar terug.')).toBe('SLECHTE_TIMING');
    expect(clusterObjection('Wij doen dit intern met ons eigen team.')).toBe('DOET_HET_ZELF');
    expect(clusterObjection('Geen behoefte aan.')).toBe('GEEN_BEHOEFTE');
    expect(clusterObjection('Wat een raar bericht.')).toBe('ANDERS');
  });

  it('aggregeert met aandelen, citaten en advies', () => {
    const stats = aggregateObjections([
      'We zijn al voorzien.',
      'Al een vaste leverancier hier.',
      'Geen budget dit jaar.',
    ]);
    expect(stats[0].cluster).toBe('AL_VOORZIEN');
    expect(stats[0].count).toBe(2);
    expect(stats[0].share).toBeCloseTo(2 / 3);
    expect(stats[0].quotes.length).toBeGreaterThan(0);
    expect(stats[0].advice.length).toBeGreaterThan(10);
  });

  it('normaliseert functietitels naar groepen', () => {
    expect(titleGroup('Algemeen Directeur')).toBe('Directie');
    expect(titleGroup('Hoofd Inkoop')).toBe('Inkoop');
    expect(titleGroup('Operationeel Manager')).toBe('Operationeel');
    expect(titleGroup(null)).toBe('Onbekend');
  });
});

describe('segmentanalyse en conclusies', () => {
  const rows = [
    ...Array.from({ length: 20 }, () => ({ industry: 'logistiek', title: 'Operationeel Manager', size: '10-50', city: 'Utrecht', replied: true, lead: false })),
    ...Array.from({ length: 20 }, () => ({ industry: 'bouw', title: 'Directeur', size: '100+', city: 'Breda', replied: false, lead: false })),
  ];

  it('berekent reply-rates per dimensie', () => {
    const segs = computeSegments(rows);
    const logistiek = segs.find((s) => s.dimension === 'branche' && s.value === 'logistiek');
    expect(logistiek?.replyRate).toBe(1);
    const bouw = segs.find((s) => s.dimension === 'branche' && s.value === 'bouw');
    expect(bouw?.replyRate).toBe(0);
  });

  it('schrijft een advies-conclusie bij een duidelijk segmentverschil', () => {
    const conclusions = writeConclusions({
      period: '2026-08', volumeSent: 40, volumeReplies: 20, volumeLeads: 2, volumeCalls: 0,
      segmentStats: computeSegments(rows),
      classificationStats: { NOT_NOW: 4 },
      objectionClusters: aggregateObjections(['al voorzien', 'al voorzien', 'zijn al voorzien hoor']),
      timingStats: { '2': 8, '3': 5, '4': 3 },
    });
    expect(conclusions.some((c) => c.includes('logistiek'))).toBe(true);
    expect(conclusions.some((c) => c.includes('bezwaar'))).toBe(true);
    expect(conclusions.some((c) => c.includes('heractiverings'))).toBe(true);
  });

  it('doet geen uitspraken zonder volume', () => {
    const conclusions = writeConclusions({
      period: '2026-08', volumeSent: 3, volumeReplies: 1, volumeLeads: 0, volumeCalls: 0,
      segmentStats: computeSegments(rows.slice(0, 3)),
      classificationStats: {}, objectionClusters: [], timingStats: {},
    });
    expect(conclusions[0]).toContain('onvoldoende volume');
  });
});

describe('trends (marktbeeld)', () => {
  it('berekent reply-rate-trend en bezwaarverschuiving met delta', () => {
    const snapshots = [
      { period: '2026-06', volumeSent: 100, volumeReplies: 4, classificationStats: {}, objectionClusters: [{ cluster: 'GEEN_BUDGET', label: 'Geen budget / te duur', count: 1, share: 0.1, quotes: [], advice: '' }] },
      { period: '2026-07', volumeSent: 100, volumeReplies: 6, classificationStats: {}, objectionClusters: [{ cluster: 'GEEN_BUDGET', label: 'Geen budget / te duur', count: 3, share: 0.3, quotes: [], advice: '' }] },
    ];
    const trends = computeTrends(snapshots as never);
    const rate = trends.find((t) => t.label.startsWith('Reply-rate'));
    expect(rate?.points.map((p) => p.value)).toEqual([4, 6]);
    expect(rate?.delta).toBe(2);
    const budget = trends.find((t) => t.label.includes('Geen budget'));
    expect(budget?.points.map((p) => p.value)).toEqual([10, 30]);
    expect(budget?.delta).toBe(20);
  });
});
