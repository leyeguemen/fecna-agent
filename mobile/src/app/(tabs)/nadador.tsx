import { File, Paths } from 'expo-file-system';
import { useLocalSearchParams } from 'expo-router';
import * as Sharing from 'expo-sharing';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import Svg, { Circle, Line, Polyline } from 'react-native-svg';
import { api, apiText, Item } from '../../api';
import { c, font } from '../../theme';
import { SOURCE_NOTE } from '../../legal';
import { Avatar, Empty, ErrorText, Icon, SourceNote } from '../../ui';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const shortDate = (iso: string) => {
  const [y, m] = iso.split('-');
  return `${MESES[Number(m) - 1] ?? ''} ${y.slice(2)}`;
};
const shortEvent = (name: string) => name.split('/')[0].trim();

function spanText(first: string, last: string) {
  const days = (new Date(last).getTime() - new Date(first).getTime()) / 864e5;
  if (days >= 548) return `${Math.round(days / 365)} años`;
  if (days >= 45) return `${Math.round(days / 30)} meses`;
  return `${Math.max(1, Math.round(days))} días`;
}

// ---- Gráfica de evolución (mejor tiempo abajo, como en el diseño) ---------------
function Evolution({ points, width }: { points: Item[]; width: number }) {
  const H = 112, padX = 10, padY = 10;
  if (points.length < 2 || width <= 0) return <Empty text="Aún no hay suficientes marcas para graficar." />;
  const ms = points.map((p) => p.time_ms as number);
  const min = Math.min(...ms), max = Math.max(...ms), span = Math.max(max - min, 1);
  const xy = points.map((p, i) => [
    padX + (i * (width - 2 * padX)) / (points.length - 1),
    padY + ((p.time_ms - min) / span) * (H - 2 * padY) * -1 + (H - 2 * padY),
  ]);
  const mid = points[Math.floor(points.length / 2)];
  return (
    <View>
      <Svg width={width} height={H}>
        {[0.15, 0.5, 0.85].map((f) => (
          <Line key={f} x1={0} x2={width} y1={H * f} y2={H * f} stroke={c.border} strokeWidth={1} />
        ))}
        <Polyline points={xy.map((p) => p.join(',')).join(' ')} fill="none" stroke={c.primary} strokeWidth={2.5} strokeLinejoin="round" />
        {xy.map(([x, y], i) => (
          <Circle key={i} cx={x} cy={y} r={4.5} stroke={c.primary} strokeWidth={2.5} fill={i === xy.length - 1 ? c.primary : c.white} />
        ))}
      </Svg>
      <View style={s.axis}>
        <Text style={s.axisText}>{shortDate(points[0].date)}</Text>
        <Text style={s.axisText}>{shortDate(mid.date)}</Text>
        <Text style={s.axisText}>{shortDate(points[points.length - 1].date)}</Text>
      </View>
    </View>
  );
}

export default function Nadador() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const insets = useSafeAreaInsets();
  const [searching, setSearching] = useState(false);
  const [q, setQ] = useState('');
  const [results, setResults] = useState<Item[]>([]);
  const [profile, setProfile] = useState<Item | null>(null);
  const [selected, setSelected] = useState<Item | null>(null);
  const [history, setHistory] = useState<Item[]>([]);
  const [following, setFollowing] = useState(false);
  const [cmpOpen, setCmpOpen] = useState(false);
  const [cmpQ, setCmpQ] = useState('');
  const [cmpResults, setCmpResults] = useState<Item[]>([]);
  const [cmp, setCmp] = useState<Item | null>(null);
  const [cmpRes, setCmpRes] = useState<Item | null>(null);
  const [chartW, setChartW] = useState(0);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Historial de la prueba elegida.
  const loadHistory = useCallback(async (swimmerId: string, e: Item) => {
    setSelected(e); setHistory([]);
    const p = new URLSearchParams({ event_id: e.event_id, pool: e.pool });
    try { setHistory((await api(`/swimmers/${encodeURIComponent(swimmerId)}/history?${p}`)).items); }
    catch (err: any) { setError(err.message); }
  }, []);

  const open = useCallback(async (swimmerId: string) => {
    setLoading(true); setError(null); setCmp(null); setCmpRes(null); setCmpQ(''); setCmpOpen(false); setSearching(false);
    try {
      const p = await api(`/swimmers/${encodeURIComponent(swimmerId)}`);
      setProfile(p);
      const me = await api('/me');
      setFollowing(me.following.some((f: Item) => f.swimmer_id === swimmerId));
      // Prueba destacada: la mejor posición nacional.
      const best = [...p.top_events].sort((a: Item, b: Item) => a.national_rank - b.national_rank)[0];
      if (best) await loadHistory(swimmerId, best); else { setSelected(null); setHistory([]); }
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [loadHistory]);

  // Abre el nadador indicado, o "mi nadador" si la cuenta lo tiene vinculado.
  useEffect(() => {
    if (id) { open(id); return; }
    api('/me').then((me) => { if (me.swimmer && !profile) open(me.swimmer.swimmer_id); else if (!me.swimmer) setSearching(true); }).catch(() => setSearching(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (q.trim().length < 3) { setResults([]); return; }
    const t = setTimeout(() => {
      api(`/swimmers/search?q=${encodeURIComponent(q.trim())}`).then((r) => setResults(r.items)).catch((e) => setError(e.message));
    }, 350);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    if (cmpQ.trim().length < 3 || cmp) { setCmpResults([]); return; }
    const t = setTimeout(() => {
      api(`/swimmers/search?q=${encodeURIComponent(cmpQ.trim())}`).then((r) => setCmpResults(r.items)).catch((e) => setError(e.message));
    }, 350);
    return () => clearTimeout(t);
  }, [cmpQ, cmp]);

  useEffect(() => {
    if (!cmp || !selected || !profile) { setCmpRes(null); return; }
    const p = new URLSearchParams({ a: profile.swimmer_id, b: cmp.swimmer_id, event_id: selected.event_id, pool: selected.pool });
    api(`/swimmers/compare?${p}`).then(setCmpRes).catch((e) => setError(e.message));
  }, [cmp, selected, profile]);

  const toggleFollow = async () => {
    try { await api(`/me/following/${encodeURIComponent(profile!.swimmer_id)}`, { method: following ? 'DELETE' : 'PUT' }); setFollowing(!following); }
    catch (err: any) { setError(err.message); }
  };

  // Descarga la ficha: en web como archivo; en el teléfono con la hoja de compartir.
  const downloadFicha = async () => {
    if (!profile) return;
    setBusy(true); setError(null);
    try {
      const html = await apiText(`/swimmers/${encodeURIComponent(profile.swimmer_id)}/ficha`);
      const name = `ficha-${profile.swimmer_name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.html`;
      if (Platform.OS === 'web') {
        const blob = new Blob([html], { type: 'text/html' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); a.remove();
      } else {
        const file = new File(Paths.cache, name);
        file.create({ overwrite: true });
        file.write(html);
        if (await Sharing.isAvailableAsync()) await Sharing.shareAsync(file.uri, { mimeType: 'text/html', dialogTitle: 'Ficha del nadador' });
        else setError('Este dispositivo no permite compartir archivos.');
      }
    } catch (e: any) { setError(e.message || 'No se pudo generar la ficha.'); }
    finally { setBusy(false); }
  };

  const stats = useMemo(() => {
    if (!selected) return null;
    const pts = history.map((h) => h.points).filter((x) => typeof x === 'number');
    const delta = history.length >= 2 ? history[history.length - 1].time_ms - history[0].time_ms : null;
    return {
      best: selected.best_time as string,
      sub: `${shortEvent(selected.event_name)} · ${selected.pool}`,
      points: pts.length ? Math.max(...pts) : null,
      rank: selected.national_rank as number,
      delta,
      span: history.length >= 2 ? spanText(history[0].date, history[history.length - 1].date) : '',
    };
  }, [selected, history]);

  const sub = profile ? [profile.club, profile.league, profile.gender, profile.age != null ? `${profile.age} años` : null].filter(Boolean).join(' · ') : 'Ficha, posiciones y evolución';

  return (
    <View style={s.root}>
      <View style={[s.header, { paddingTop: (Platform.OS === 'web' ? 0 : insets.top) + 14 }]}>
        {profile ? <Avatar label={profile.swimmer_name} size={56} /> : null}
        <View style={{ flex: 1 }}>
          <Text style={s.name} numberOfLines={1}>{profile ? profile.swimmer_name : 'Nadador'}</Text>
          <Text style={s.subtitle} numberOfLines={2}>{sub}</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }} keyboardShouldPersistTaps="handled">
        {profile ? (
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <Pressable onPress={toggleFollow} style={[s.action, following && { backgroundColor: c.chip, borderColor: c.accent }]}>
              <Text style={s.actionText}>{following ? '✓ Siguiendo' : '+ Seguir'}</Text>
            </Pressable>
            <Pressable accessibilityLabel="Buscar otro nadador" onPress={() => setSearching((v) => !v)} style={[s.action, { flexDirection: 'row', gap: 6 }]}>
              <Icon name="search" size={14} color={c.primary} />
              <Text style={s.actionText}>Buscar otro</Text>
            </Pressable>
          </View>
        ) : null}
        {searching ? (
          <View style={{ gap: 8 }}>
            <TextInput autoFocus value={q} onChangeText={setQ} placeholder="Buscar por nombre (mín. 3 letras)" placeholderTextColor="#8AA3B5" style={s.search} />
            {results.map((r) => (
              <Pressable key={r.swimmer_id} style={s.row} onPress={() => { setQ(''); setResults([]); open(r.swimmer_id); }}>
                <View style={{ flex: 1 }}>
                  <Text style={s.rowName}>{r.swimmer_name}</Text>
                  <Text style={s.small}>{[r.club, r.league].filter(Boolean).join(' · ')}</Text>
                </View>
              </Pressable>
            ))}
          </View>
        ) : null}
        <ErrorText text={error} />
        {loading ? <ActivityIndicator color={c.primary} style={{ marginTop: 24 }} /> : null}

        {profile && !loading ? (
          <>
            {stats ? (
              <>
                <View style={{ flexDirection: 'row', gap: 12 }}>
                  <View style={[s.card, { flex: 1 }]}>
                    <Text style={s.small}>Mejor marca</Text>
                    <Text style={s.big}>{stats.best}</Text>
                    <Text style={s.small} numberOfLines={1}>{stats.sub}</Text>
                  </View>
                  <View style={[s.card, { flex: 1 }]}>
                    <Text style={s.small}>Puntos WA</Text>
                    <Text style={s.big}>{stats.points ?? '—'}</Text>
                    <Text style={s.small}>Ranking nac. #{stats.rank}</Text>
                  </View>
                </View>

                <View style={s.card} onLayout={(e) => setChartW(e.nativeEvent.layout.width - 28)}>
                  <View style={s.cardHead}>
                    <Text style={s.cardTitle} numberOfLines={1}>Evolución · {shortEvent(selected!.event_name)}</Text>
                    {stats.delta != null ? (
                      <View style={s.chip}>
                        <Text style={s.chipText}>{stats.delta <= 0 ? '−' : '+'}{(Math.abs(stats.delta) / 1000).toFixed(2)} s en {stats.span}</Text>
                      </View>
                    ) : null}
                  </View>
                  <Evolution points={history} width={chartW} />
                </View>
              </>
            ) : null}

            <View style={{ flexDirection: 'row', gap: 12 }}>
              <Pressable style={[s.btn, s.btnPrimary]} onPress={() => setCmpOpen((v) => !v)}>
                <Text style={[s.btnText, { color: c.white }]}>Comparar con…</Text>
              </Pressable>
              <Pressable style={[s.btn, s.btnOutline, busy && { opacity: 0.6 }]} onPress={downloadFicha} disabled={busy}>
                {busy ? <ActivityIndicator color={c.primary} /> : <Text style={[s.btnText, { color: c.primary }]}>Descargar ficha</Text>}
              </Pressable>
            </View>

            {cmpOpen ? (
              <View style={s.card}>
                {!selected ? <Text style={s.small}>Elige primero una prueba.</Text> : !cmp ? (
                  <>
                    <Text style={s.cardTitle}>Comparar en {shortEvent(selected.event_name)} · {selected.pool}</Text>
                    <TextInput value={cmpQ} onChangeText={setCmpQ} placeholder="Nombre del otro nadador" placeholderTextColor="#8AA3B5" style={[s.search, { marginTop: 8 }]} />
                    {cmpResults.map((r) => (
                      <Pressable key={r.swimmer_id} style={[s.row, { marginTop: 8 }]} onPress={() => { setCmp(r); setCmpResults([]); }}>
                        <Text style={s.rowName}>{r.swimmer_name}</Text>
                      </Pressable>
                    ))}
                  </>
                ) : (
                  <View style={{ gap: 6 }}>
                    <Text style={s.cardTitle}>Comparar en {shortEvent(selected.event_name)} · {selected.pool}</Text>
                    {cmpRes ? (
                      <>
                        <Text style={s.rowName}>{cmpRes.a?.swimmer_name ?? profile.swimmer_name}: {cmpRes.a?.time ?? 'sin marca'}</Text>
                        <Text style={s.rowName}>{cmpRes.b?.swimmer_name ?? cmp.swimmer_name}: {cmpRes.b?.time ?? 'sin marca'}</Text>
                        <Text style={s.small}>{cmpRes.diff ? `Diferencia: ${cmpRes.diff}` : 'No hay marcas de ambos en esta prueba.'}</Text>
                      </>
                    ) : null}
                    <Pressable onPress={() => { setCmp(null); setCmpRes(null); setCmpQ(''); }}><Text style={s.link}>Cambiar rival</Text></Pressable>
                  </View>
                )}
              </View>
            ) : null}

            <Text style={s.section}>Mejores marcas por prueba</Text>
            {profile.top_events.map((e: Item) => {
              const on = selected?.event_id === e.event_id && selected?.pool === e.pool;
              return (
                <Pressable key={`${e.event_id}-${e.pool}`} onPress={() => loadHistory(profile.swimmer_id, e)} style={[s.event, on && { borderColor: c.primary }]}>
                  <Text style={s.rowName}>{shortEvent(e.event_name)}{e.pool === 'SC' ? ' · corta' : ''}</Text>
                  <Text style={s.eventTime}>{e.best_time}</Text>
                </Pressable>
              );
            })}
            <SourceNote text={SOURCE_NOTE} />
          </>
        ) : null}

        {!profile && !loading && !searching ? <Empty text="Busca un nadador o abre uno desde el Ranking." /> : null}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  header: { backgroundColor: c.deep, paddingHorizontal: 16, paddingBottom: 16, flexDirection: 'row', alignItems: 'center', gap: 12 },
  name: { color: c.white, fontFamily: font.title, fontSize: 20 },
  subtitle: { color: c.headerSub, fontFamily: font.body, fontSize: 12, marginTop: 2 },
  action: { alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: c.border, borderRadius: 16, paddingHorizontal: 12, paddingVertical: 7, backgroundColor: c.white },
  actionText: { color: c.primary, fontFamily: font.semi, fontSize: 12 },
  search: { height: 48, borderWidth: 1, borderColor: c.input, borderRadius: 14, paddingHorizontal: 14, backgroundColor: c.white, fontFamily: font.body },
  card: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 16, padding: 14, gap: 2 },
  cardHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10, gap: 8 },
  cardTitle: { fontFamily: font.bold, fontSize: 14, color: c.text, flexShrink: 1 },
  chip: { backgroundColor: c.chip, borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4 },
  chipText: { color: c.deep, fontFamily: font.semi, fontSize: 11 },
  big: { fontFamily: font.title, fontSize: 26, color: c.text, marginVertical: 2 },
  small: { fontFamily: font.body, color: c.muted, fontSize: 12 },
  axis: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 6, paddingHorizontal: 4 },
  axisText: { fontFamily: font.body, color: c.muted, fontSize: 11 },
  btn: { flex: 1, height: 52, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  btnPrimary: { backgroundColor: c.primary },
  btnOutline: { backgroundColor: c.white, borderWidth: 1.5, borderColor: c.primary },
  btnText: { fontFamily: font.bold, fontSize: 14 },
  section: { fontFamily: font.bold, fontSize: 14, color: c.text, marginTop: 6 },
  event: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: c.white, borderWidth: 1.5, borderColor: c.border, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 14 },
  eventTime: { fontFamily: font.bold, fontSize: 15, color: c.text },
  row: { flexDirection: 'row', alignItems: 'center', backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 14, padding: 12 },
  rowName: { fontFamily: font.semi, color: c.text, fontSize: 14 },
  link: { color: c.primary, fontFamily: font.semi, fontSize: 13 },
});
