// Detalle de una prueba del programa (Torneos → tarjeta de un nadador → una prueba).
// Casi todo sale del programa ya descargado; la mejor marca, de la ficha del nadador.
import { router } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { BackHandler, Platform, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { api, Item } from './api';
import { dayLabel } from './fechas';
import { c, font } from './theme';
import { Avatar, Icon } from './ui';

/** «16:30» → «4:30 p. m.» */
export function hour12(hhmm?: string | null): string {
  const m = hhmm ? /^(\d{1,2}):(\d{2})/.exec(hhmm) : null;
  if (!m) return '';
  const h = Number(m[1]);
  return `${h % 12 || 12}:${m[2]} ${h < 12 ? 'a. m.' : 'p. m.'}`;
}

/** Estado según la fecha y la hora programadas (el programa no trae resultados). */
export function status(date?: string | null, time?: string | null, now = new Date()): { title: string; sub: string; past: boolean } {
  const d = date ? /^(\d{4})-(\d{2})-(\d{2})/.exec(date) : null;
  if (!d) return { title: 'Programada', sub: 'Sin fecha en el programa', past: false };
  const day = new Date(Number(d[1]), Number(d[2]) - 1, Number(d[3]));
  const today = new Date(now); today.setHours(0, 0, 0, 0);
  const n = Math.round((day.getTime() - today.getTime()) / 86_400_000);
  if (n < 0) return { title: 'Ya se nadó', sub: dayLabel(date), past: true };
  if (n === 0) {
    const t = time ? /^(\d{1,2}):(\d{2})/.exec(time) : null;
    if (t && now.getHours() * 60 + now.getMinutes() > Number(t[1]) * 60 + Number(t[2]) + 15) {
      return { title: 'Ya se nadó', sub: 'Hoy', past: true };
    }
    return { title: 'Hoy', sub: time ? hour12(time) : 'Hora por confirmar', past: false };
  }
  return { title: 'Por nadar', sub: n === 1 ? 'Mañana' : `En ${n} días`, past: false };
}

const secs = (ms: number) => (ms / 1000).toFixed(2);

export function PruebaDetalle({ entry, rows, compName, pool, mine, onBack }: {
  entry: Item; rows: Item[]; compName: string; pool?: string | null; mine: boolean; onBack: () => void;
}) {
  const insets = useSafeAreaInsets();
  const [best, setBest] = useState<Item | null>(null);

  // Atrás de Android vuelve al programa, no sale de Torneos.
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => { onBack(); return true; });
    return () => sub.remove();
  }, [onBack]);

  // Mejor marca del ranking en esta prueba (misma piscina del torneo si se sabe).
  useEffect(() => {
    if (!entry.swimmer_id || !entry.event_id) return;
    let alive = true;
    api(`/swimmers/${encodeURIComponent(entry.swimmer_id)}`).then((p) => {
      const same = p.top_events.filter((e: Item) => e.event_id === entry.event_id);
      const pick = same.find((e: Item) => !pool || e.pool === pool) ?? (pool ? null : same[0]);
      if (alive) setBest(pick ?? null);
    }).catch(() => {});
    return () => { alive = false; };
  }, [entry.swimmer_id, entry.event_id, pool]);

  const info = useMemo(() => {
    const ev = rows.filter((r) => r.event_number === entry.event_number);
    const seeded = ev.filter((r) => r.seed_ms != null).sort((a, b) => a.seed_ms - b.seed_ms);
    const seedPos = entry.seed_ms != null ? seeded.indexOf(entry) + 1 : 0;
    const heats = Math.max(...ev.map((r) => r.heat ?? 0));
    const lanes = Math.max(...ev.map((r) => r.lane ?? 0));
    const heatMates = ev.filter((r) => r.heat === entry.heat).sort((a, b) => (a.lane ?? 99) - (b.lane ?? 99));
    return { total: ev.length, seedPos, heats, lanes, heatMates };
  }, [rows, entry]);

  const st = status(entry.date, entry.start_time);
  const when = [dayLabel(entry.date), hour12(entry.start_time), entry.session_no ? `Jornada ${entry.session_no}` : null].filter(Boolean).join(' · ');
  const diff = best && entry.seed_ms != null ? best.best_ms - entry.seed_ms : null;

  return (
    <View style={s.root}>
      <View style={[s.header, { paddingTop: (Platform.OS === 'web' ? 0 : insets.top) + 6 }]}>
        <View style={s.bar}>
          <Pressable onPress={onBack} accessibilityRole="button" accessibilityLabel="Volver al programa" hitSlop={8} style={s.backBtn}>
            <Icon name="back" color={c.white} size={22} />
          </Pressable>
          <Text style={s.barTitle}>Detalle de la prueba</Text>
        </View>
        <View style={s.heroRow}>
          <View style={s.badge}>
            <Text style={s.badgeLabel}>PRUEBA</Text>
            <Text style={s.badgeNum}>{entry.event_number ?? '—'}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={s.comp} numberOfLines={1}>{compName}</Text>
            <Text style={s.event}>{entry.event_label}</Text>
            {when ? <Text style={s.comp}>{when}</Text> : null}
          </View>
        </View>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 24 }}>
        <Pressable
          onPress={entry.swimmer_id ? () => router.push({ pathname: '/nadador', params: { id: entry.swimmer_id } }) : undefined}
          accessibilityRole={entry.swimmer_id ? 'button' : undefined}
          style={[s.card, s.swimmer, mine && { borderColor: '#9EDCEB' }]}>
          <Avatar label={entry.swimmer_name} size={42} />
          <View style={{ flex: 1 }}>
            <Text style={s.name}>{entry.swimmer_name}</Text>
            <Text style={s.sub}>
              {[entry.club_code, entry.age != null ? `${entry.age} años` : null].filter(Boolean).join(' · ')}
              {mine ? <Text style={{ color: c.primary, fontFamily: font.semi }}>{'  ★ Tu nadador'}</Text> : null}
            </Text>
          </View>
          {entry.swimmer_id ? (
            <>
              <Text style={s.link}>Ver ficha</Text>
              <Icon name="chevron" size={16} color={c.primary} />
            </>
          ) : null}
        </Pressable>

        {entry.session_no || entry.start_time ? (
          <View style={[s.card, { flexDirection: 'row', alignItems: 'center', gap: 12 }]}>
            <Icon name="calendar" size={22} color={c.primary} />
            <View style={{ flex: 1 }}>
              <Text style={s.sub}>Jornada</Text>
              <Text style={s.bestTime}>{entry.session_no ? `Jornada ${entry.session_no}` : 'Sin jornada'}</Text>
              {entry.date ? <Text style={s.sub}>{dayLabel(entry.date)}</Text> : null}
            </View>
            {entry.start_time ? (
              <View style={{ alignItems: 'flex-end' }}>
                <Text style={s.sub}>Hora aproximada</Text>
                <Text style={s.bestTime}>{hour12(entry.start_time)}</Text>
              </View>
            ) : null}
          </View>
        ) : null}

        <View style={s.grid}>
          <View style={[s.card, s.tile]}>
            <Text style={s.tileLabel}>SERIE</Text>
            <Text style={s.tileBig}>{entry.heat ?? '—'}</Text>
            {info.heats > 0 ? <Text style={s.sub}>de {info.heats}</Text> : null}
          </View>
          <View style={[s.card, s.tile]}>
            <Text style={s.tileLabel}>CARRIL</Text>
            <Text style={s.tileBig}>{entry.lane ?? '—'}</Text>
            {info.lanes > 0 ? <Text style={s.sub}>de {info.lanes}</Text> : null}
          </View>
          <View style={[s.card, s.half]}>
            <Text style={s.sub}>Tiempo de inscripción</Text>
            <Text style={s.mid}>{entry.seed ?? 'Sin tiempo'}</Text>
            {info.seedPos > 0 ? <Text style={s.sub}>Siembra {info.seedPos} de {info.total}</Text> : null}
          </View>
          <View style={[s.card, s.half, !st.past && { backgroundColor: c.chip, borderColor: '#9EDCEB' }]}>
            <Text style={[s.sub, !st.past && { color: c.deep }]}>Estado</Text>
            <Text style={[s.mid, { fontSize: 20 }, !st.past && { color: c.deep }]}>{st.title}</Text>
            <Text style={[s.sub, !st.past && { color: c.deep }]}>{st.sub}</Text>
          </View>
        </View>

        {best ? (
          <View style={[s.card, { flexDirection: 'row', alignItems: 'center', gap: 12 }]}>
            <Icon name="ranking" size={22} color={c.primary} />
            <View style={{ flex: 1 }}>
              <Text style={s.sub}>Mejor marca en el ranking · {best.pool}</Text>
              <Text style={{ marginTop: 2 }}>
                <Text style={s.bestTime}>{best.best_time}</Text>
                {best.national_rank ? <Text style={s.sub}>{`  · #${best.national_rank} nacional`}</Text> : null}
              </Text>
            </View>
            {diff != null && diff !== 0 ? (
              <Text style={[s.diff, diff > 0 && { color: c.muted, backgroundColor: '#EEF3F7' }]}>
                {diff < 0 ? '−' : '+'}{secs(Math.abs(diff))} vs inscripción
              </Text>
            ) : null}
          </View>
        ) : null}

        {info.heatMates.length > 1 ? (
          <View>
            <Text style={s.overline}>SERIE {entry.heat} · QUIÉNES NADAN CON {entry.swimmer_name.split(' ')[0].toUpperCase()}</Text>
            <View style={[s.card, { padding: 0, overflow: 'hidden' }]}>
              {info.heatMates.map((r, i) => {
                const me = r === entry; // mismo objeto del programa descargado
                return (
                  <View key={i} style={[s.mate, i > 0 && { borderTopWidth: 1, borderTopColor: '#E3EDF3' }, me && { backgroundColor: c.chip }]}>
                    <View style={[s.lane, me && { backgroundColor: c.primary }]}>
                      <Text style={[s.laneText, me && { color: c.white }]}>{r.lane ?? '—'}</Text>
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={[s.mateName, me && { fontFamily: font.bold }]} numberOfLines={1}>{r.swimmer_name}</Text>
                      <Text style={s.small}>{r.club_code}</Text>
                    </View>
                    <Text style={s.mateSeed}>{r.seed ?? '—'}</Text>
                  </View>
                );
              })}
            </View>
          </View>
        ) : null}

        <Text style={[s.small, { textAlign: 'center', lineHeight: 16 }]}>Datos del programa publicado por el organizador. Los resultados no se muestran aquí.</Text>
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  header: { backgroundColor: c.deep, paddingBottom: 18 },
  bar: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, height: 52 },
  backBtn: { width: 44, height: 44, borderRadius: 22, alignItems: 'center', justifyContent: 'center' },
  barTitle: { color: c.white, fontFamily: font.title, fontSize: 18 },
  heroRow: { flexDirection: 'row', alignItems: 'center', gap: 14, paddingHorizontal: 16, paddingTop: 4 },
  badge: { width: 64, height: 64, borderRadius: 18, backgroundColor: c.accent, alignItems: 'center', justifyContent: 'center' },
  badgeLabel: { color: c.deep, fontFamily: font.bold, fontSize: 10, letterSpacing: 0.6 },
  badgeNum: { color: c.deep, fontFamily: font.title, fontSize: 26, lineHeight: 28 },
  comp: { color: c.headerSub, fontFamily: font.body, fontSize: 12, marginTop: 2 },
  event: { color: c.white, fontFamily: font.title, fontSize: 19, lineHeight: 23, marginTop: 2 },
  card: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 14, padding: 12 },
  swimmer: { flexDirection: 'row', alignItems: 'center', gap: 12, borderRadius: 16 },
  name: { fontFamily: font.semi, fontSize: 15, color: c.text },
  sub: { fontFamily: font.body, fontSize: 12, color: c.muted, marginTop: 2 },
  small: { fontFamily: font.body, fontSize: 11, color: c.muted },
  link: { color: c.primary, fontFamily: font.semi, fontSize: 12 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  tile: { flexBasis: '47%', flexGrow: 1, alignItems: 'center' },
  half: { flexBasis: '47%', flexGrow: 1 },
  tileLabel: { fontFamily: font.semi, fontSize: 11, color: c.muted, letterSpacing: 0.4 },
  tileBig: { fontFamily: font.title, fontSize: 30, color: c.deep },
  mid: { fontFamily: font.title, fontSize: 22, color: c.text },
  bestTime: { fontFamily: font.title, fontSize: 16, color: c.text },
  diff: { fontFamily: font.bold, fontSize: 11, color: '#1B8A4B', backgroundColor: '#E8F6EE', borderRadius: 10, paddingHorizontal: 8, paddingVertical: 4, overflow: 'hidden' },
  overline: { fontFamily: font.semi, fontSize: 12, color: c.muted, letterSpacing: 0.4, marginBottom: 8, marginTop: 4 },
  mate: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 14, paddingVertical: 9 },
  lane: { width: 26, height: 26, borderRadius: 13, backgroundColor: '#E3EDF3', alignItems: 'center', justifyContent: 'center' },
  laneText: { fontFamily: font.bold, fontSize: 12, color: c.deep },
  mateName: { fontFamily: font.medium, fontSize: 13, color: c.text },
  mateSeed: { fontFamily: font.title, fontSize: 13, color: c.deep },
});
