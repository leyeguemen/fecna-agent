import { useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import Svg, { Circle, Polyline } from 'react-native-svg';
import { api, Item } from '../../api';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Card, Empty, ErrorText, Header } from '../../ui';

const W = 320, H = 120;

function Evolution({ points }: { points: Item[] }) {
  if (points.length < 2) return <Empty text="Aún no hay suficientes marcas para graficar." />;
  const ms = points.map((p) => p.time_ms as number);
  const min = Math.min(...ms), max = Math.max(...ms), span = Math.max(max - min, 1);
  const xy = points.map((p, i) => [8 + (i * (W - 16)) / (points.length - 1), 8 + ((p.time_ms - min) / span) * (H - 16)]);
  return (
    <View>
      <Svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`}>
        <Polyline points={xy.map((p) => p.join(',')).join(' ')} fill="none" stroke={c.primary} strokeWidth={2} />
        {xy.map(([x, y], i) => <Circle key={i} cx={x} cy={y} r={3} fill={c.accent} />)}
      </Svg>
      <Text style={s.sub}>Más abajo = más rápido · {points[0].date} → {points[points.length - 1].date}</Text>
    </View>
  );
}

export default function Nadador() {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const [q, setQ] = useState('');
  const [results, setResults] = useState<Item[]>([]);
  const [profile, setProfile] = useState<Item | null>(null);
  const [selected, setSelected] = useState<Item | null>(null);
  const [history, setHistory] = useState<Item[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const open = useCallback(async (swimmerId: string) => {
    setLoading(true); setError(null); setSelected(null); setHistory([]);
    try { setProfile(await api(`/swimmers/${encodeURIComponent(swimmerId)}`)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { if (id) open(id); }, [id, open]);

  useEffect(() => {
    if (q.trim().length < 3) { setResults([]); return; }
    const t = setTimeout(() => {
      api(`/swimmers/search?q=${encodeURIComponent(q.trim())}`).then((r) => setResults(r.items)).catch((e) => setError(e.message));
    }, 350);
    return () => clearTimeout(t);
  }, [q]);

  const pick = async (e: Item) => {
    setSelected(e);
    const p = new URLSearchParams({ event_id: e.event_id, pool: e.pool });
    try { setHistory((await api(`/swimmers/${encodeURIComponent(profile!.swimmer_id)}/history?${p}`)).items); }
    catch (err: any) { setError(err.message); }
  };

  return (
    <View style={s.root}>
      <Header title="Nadador" subtitle="Ficha, posiciones y evolución" right={<ProfileButton />} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }} keyboardShouldPersistTaps="handled">
        <TextInput value={q} onChangeText={setQ} placeholder="Buscar por nombre (mín. 3 letras)" placeholderTextColor="#8AA3B5" style={s.search} />
        <ErrorText text={error} />
        {results.map((r) => (
          <Pressable key={r.swimmer_id} style={s.result} onPress={() => { setQ(''); setResults([]); open(r.swimmer_id); }}>
            <Text style={s.name}>{r.swimmer_name}</Text>
            <Text style={s.sub}>{[r.club, r.league].filter(Boolean).join(' · ')}</Text>
          </Pressable>
        ))}
        {loading && <ActivityIndicator color={c.primary} />}
        {profile && (
          <>
            <Card>
              <Text style={s.title}>{profile.swimmer_name}</Text>
              <Text style={s.sub}>{[profile.club, profile.league, profile.age != null ? `${profile.age} años` : null].filter(Boolean).join(' · ')}</Text>
            </Card>
            <Text style={s.section}>MEJORES MARCAS (toca una para ver su evolución)</Text>
            {profile.top_events.map((e: Item) => (
              <Pressable key={`${e.event_id}-${e.pool}`} onPress={() => pick(e)}
                style={[s.event, selected?.event_id === e.event_id && selected?.pool === e.pool && { borderColor: c.primary }]}>
                <View style={{ flex: 1 }}>
                  <Text style={s.name}>{e.event_name} · {e.pool}</Text>
                  <Text style={s.sub}>Nacional #{e.national_rank}/{e.national_total} · Liga #{e.league_rank}/{e.league_total}</Text>
                </View>
                <Text style={s.time}>{e.best_time}</Text>
              </Pressable>
            ))}
            {selected && <Card><Evolution points={history} /></Card>}
          </>
        )}
        {!profile && !loading && results.length === 0 && <Empty text="Busca un nadador o abre uno desde el Ranking." />}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  search: { height: 48, borderWidth: 1, borderColor: c.input, borderRadius: 14, paddingHorizontal: 14, backgroundColor: c.white, fontFamily: font.body },
  result: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 14, padding: 12 },
  title: { fontFamily: font.title, fontSize: 20, color: c.deep },
  name: { fontFamily: font.semi, color: c.text, fontSize: 14 },
  sub: { fontFamily: font.body, color: c.muted, fontSize: 12, marginTop: 2 },
  section: { fontFamily: font.bold, color: c.muted, fontSize: 11, letterSpacing: 0.6, marginTop: 4 },
  event: { flexDirection: 'row', alignItems: 'center', backgroundColor: c.white, borderWidth: 1.5, borderColor: c.border, borderRadius: 14, padding: 12 },
  time: { fontFamily: font.bold, color: c.deep, fontSize: 16 },
});
