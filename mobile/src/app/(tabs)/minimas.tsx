import { useLocalSearchParams } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { api, Item } from '../../api';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Avatar, Card, Chip, Empty, ErrorText, Header, Icon } from '../../ui';

type Mode = 'n' | 'c';
type Filter = 'todas' | 'cumple' | 'falta';

// Colores de estado: se distinguen también por texto e icono, no solo por el color.
const OK = { bg: '#E3F6EC', fg: '#0B6B43' };
const MISS = { bg: '#FFF1DC', fg: '#8A4B00' };
const NONE = { bg: '#EEF3F7', fg: '#4A6378' };

export default function Minimas() {
  const [mode, setMode] = useState<Mode>('n');
  const [tournaments, setTournaments] = useState<Item[]>([]);
  const [tournament, setTournament] = useState('interligas');
  const [linkedId, setLinkedId] = useState<string | null>(null);
  const [swimmerId, setSwimmerId] = useState<string | null>(null);
  const [data, setData] = useState<Item | null>(null);
  const [filter, setFilter] = useState<Filter>('todas');
  const [picking, setPicking] = useState(false);
  const [q, setQ] = useState('');
  const [results, setResults] = useState<Item[]>([]);
  const [category, setCategory] = useState<string | null>(null);
  const [gender, setGender] = useState<'M' | 'F'>('M');
  const [table, setTable] = useState<Item | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api('/minimas/torneos').then((r) => setTournaments(r.items)).catch((e) => setError(e.message));
    api('/me').then((me) => {
      if (me.swimmer) { setLinkedId(me.swimmer.swimmer_id); setSwimmerId(me.swimmer.swimmer_id); }
      else { setPicking(true); setLoading(false); }
    }).catch(() => { setPicking(true); setLoading(false); });
  }, []);

  // Desde el Inicio (?torneo=…&nadador=…): abre el campeonato y el nadador de la tarjeta.
  // La pestaña queda montada, así que se aplica cada vez que cambian los parámetros.
  const { torneo, nadador } = useLocalSearchParams<{ torneo?: string; nadador?: string }>();
  const paramKey = torneo ? `${torneo}|${nadador ?? ''}` : null;
  const [appliedKey, setAppliedKey] = useState<string | null>(null);
  if (torneo && paramKey !== appliedKey) {
    setAppliedKey(paramKey);
    setMode('n');
    setTournament(torneo);
    if (nadador) { setSwimmerId(nadador); setPicking(false); }
  }

  const loadSwimmer = useCallback(async () => {
    if (!swimmerId) return;
    setLoading(true); setError(null);
    try { setData(await api(`/minimas/nadador/${encodeURIComponent(swimmerId)}?tournament=${tournament}`)); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [swimmerId, tournament]);
  useEffect(() => { loadSwimmer(); }, [loadSwimmer]);

  const cats: Item[] = tournaments.find((t) => t.id === tournament)?.categories ?? [];
  // La categoría de la tabla general parte de la del nadador (si aplica) y si no, de la primera del campeonato.
  useEffect(() => {
    if (!cats.length) return;
    if (!category || !cats.some((x) => x.id === category)) setCategory(data?.category && cats.some((x) => x.id === data.category) ? data.category : cats[0].id);
  }, [tournament, tournaments, data]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (data?.gender === 'M' || data?.gender === 'F') setGender(data.gender); }, [data?.swimmer_id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    // La categoría puede ser todavía la del campeonato anterior: se espera a que se corrija antes de pedir la tabla.
    if (mode !== 'c' || !category || !cats.some((x) => x.id === category)) return;
    let current = true;
    api(`/minimas/tabla?tournament=${tournament}&category=${category}&gender=${gender}`)
      .then((r) => { if (current) { setTable(r); setError(null); } })
      .catch((e) => { if (current) setError(e.message); });
    return () => { current = false; };
  }, [mode, tournament, category, gender, tournaments]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!picking || q.trim().length < 3) { setResults([]); return; }
    const t = setTimeout(() => api(`/swimmers/search?q=${encodeURIComponent(q.trim())}`).then((r) => setResults(r.items)).catch((e) => setError(e.message)), 350);
    return () => clearTimeout(t);
  }, [q, picking]);

  const choose = (id: string) => { setSwimmerId(id); setPicking(false); setQ(''); setResults([]); setData(null); };

  const rows: Item[] = (data?.rows ?? []).filter((r: Item) => filter === 'todas' || (filter === 'cumple' ? r.status === 'cumple' : r.status !== 'cumple'));
  const pct = data?.total ? Math.round((data.met / data.total) * 100) : 0;

  const tournamentChips = (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ flexGrow: 0 }} contentContainerStyle={{ gap: 8 }}>
      {tournaments.map((t) => <Chip key={t.id} label={t.label} selected={tournament === t.id} onPress={() => setTournament(t.id)} />)}
    </ScrollView>
  );

  return (
    <View style={s.root}>
      <Header title="Marcas mínimas" subtitle={`Campeonatos nacionales ${tournaments[0]?.year ?? ''}`.trim()} right={<ProfileButton />} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }} keyboardShouldPersistTaps="handled">
        <View style={s.seg}>
          {([['n', 'Mi nadador'], ['c', 'Por categoría']] as const).map(([k, label]) => (
            <Pressable key={k} accessibilityRole="button" onPress={() => { setMode(k); setPicking(false); }} style={[s.segBtn, mode === k && { backgroundColor: c.deep }]}>
              <Text style={[s.segText, mode === k && { color: c.white }]}>{label}</Text>
            </Pressable>
          ))}
        </View>
        <ErrorText text={error} />

        {mode === 'n' && picking ? (
          <>
            <View>
              <TextInput value={q} onChangeText={setQ} placeholder="Buscar nadador (mín. 3 letras)" placeholderTextColor="#8AA3B5" autoCapitalize="none" style={s.search} />
              <View style={{ position: 'absolute', left: 13, top: 13 }}><Icon name="search" size={20} /></View>
            </View>
            {linkedId && linkedId !== swimmerId ? (
              <Pressable onPress={() => choose(linkedId)} accessibilityRole="button" style={s.smallBtn}><Text style={s.smallBtnText}>Volver a mi nadador</Text></Pressable>
            ) : null}
            {results.map((it) => (
              <Pressable key={it.swimmer_id} onPress={() => choose(it.swimmer_id)} accessibilityRole="button" style={s.opt}>
                <Text style={s.name} numberOfLines={1}>{it.swimmer_name}</Text>
                <Text style={s.sub} numberOfLines={1}>{[it.club, it.league].filter(Boolean).join(' · ')}</Text>
              </Pressable>
            ))}
            {!linkedId && !results.length ? <Text style={s.sub}>Busca un nadador para ver sus marcas mínimas. Si vinculas el tuyo en tu perfil, aparecerá aquí por defecto.</Text> : null}
          </>
        ) : null}

        {mode === 'n' && !picking ? (
          <>
            {data ? (
              <Card>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                  <Avatar label={data.swimmer_name} size={44} />
                  <View style={{ flex: 1 }}>
                    <Text style={s.name} numberOfLines={1}>{data.swimmer_name}</Text>
                    <Text style={s.sub}>{[data.category_label, data.gender === 'F' ? 'Femenino' : data.gender === 'M' ? 'Masculino' : null].filter(Boolean).join(' · ') || 'Sin categoría'}</Text>
                    {data.swimmer_id === linkedId ? <Text style={s.linked}>Vinculado a tu cuenta</Text> : null}
                  </View>
                  <Pressable onPress={() => setPicking(true)} accessibilityRole="button" style={s.smallBtn}><Text style={s.smallBtnText}>Cambiar</Text></Pressable>
                </View>
              </Card>
            ) : null}
            {tournamentChips}
            {loading && !data ? <ActivityIndicator color={c.primary} style={{ marginTop: 16 }} /> : null}
            {data && !data.applicable ? (
              <Empty text={data.category === null && data.age != null
                ? `Por su edad (${data.age} años) no tiene categoría en este campeonato. Prueba con otro.`
                : 'No hay datos suficientes (género o fecha de nacimiento) para calcular su categoría.'} />
            ) : null}
            {data?.applicable ? (
              <>
                <Card>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' }}>
                    <Text style={s.big}>Cumples {data.met} de {data.total}</Text>
                    <Text style={s.sub}>pruebas</Text>
                  </View>
                  <View style={s.bar}><View style={[s.barFill, { width: `${pct}%` }]} /></View>
                  <Text style={s.sub}>Piscina larga (50 m). Para competir basta con cumplir al menos una (reglamento 13.4).</Text>
                </Card>
                <View style={{ flexDirection: 'row', gap: 8 }}>
                  <Chip label="Todas" selected={filter === 'todas'} onPress={() => setFilter('todas')} />
                  <Chip label="Cumple" selected={filter === 'cumple'} onPress={() => setFilter('cumple')} />
                  <Chip label="Me falta" selected={filter === 'falta'} onPress={() => setFilter('falta')} />
                </View>
                <View style={s.list}>
                  {rows.map((r, i) => {
                    const st = r.status === 'cumple' ? OK : r.status === 'falta' ? MISS : NONE;
                    return (
                      <View key={r.event_id} style={[s.row, i < rows.length - 1 && s.rowLine]}>
                        <Text style={s.event}>{r.event}</Text>
                        <Text style={[s.sub, { flex: 1, marginTop: 0, lineHeight: 18 }]}>Mínima <Text style={s.bold}>{r.minima}</Text>{'\n'}Tu marca <Text style={s.bold}>{r.best ?? '—'}</Text></Text>
                        <View style={[s.pill, { backgroundColor: st.bg }]}>
                          {r.status === 'cumple' ? <Icon name="check" size={14} color={st.fg} /> : null}
                          <Text style={[s.pillText, { color: st.fg }]}>{r.status === 'cumple' ? 'Cumple' : r.status === 'falta' ? `Falta ${r.diff}` : 'Sin marca'}</Text>
                        </View>
                      </View>
                    );
                  })}
                  {!rows.length ? <Text style={[s.sub, { padding: 14 }]}>Ninguna prueba en este filtro.</Text> : null}
                </View>
              </>
            ) : null}
          </>
        ) : null}

        {mode === 'c' ? (
          <>
            {tournamentChips}
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ flexGrow: 0 }} contentContainerStyle={{ gap: 8 }}>
              {cats.map((x) => <Chip key={x.id} label={x.label} selected={category === x.id} onPress={() => setCategory(x.id)} />)}
            </ScrollView>
            <View style={{ flexDirection: 'row', gap: 8 }}>
              <Chip label="Masculino" selected={gender === 'M'} onPress={() => setGender('M')} />
              <Chip label="Femenino" selected={gender === 'F'} onPress={() => setGender('F')} />
            </View>
            <Text style={s.h}>MARCA MÍNIMA POR PRUEBA</Text>
            <View style={s.list}>
              {(table?.rows ?? []).map((r: Item, i: number, a: Item[]) => (
                <View key={r.event_id} style={[s.row, { justifyContent: 'space-between' }, i < a.length - 1 && s.rowLine]}>
                  <Text style={s.event}>{r.event}</Text>
                  <Text style={s.time}>{r.minima}</Text>
                </View>
              ))}
              {table && !table.rows.length ? <Text style={[s.sub, { padding: 14 }]}>Esta categoría no tiene marcas en este campeonato.</Text> : null}
            </View>
            <Text style={s.sub}>Fuente: Reglamento FECNA, art. 13. Marcas de piscina larga (50 m).</Text>
          </>
        ) : null}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  seg: { flexDirection: 'row', borderWidth: 1.5, borderColor: c.deep, borderRadius: 12, overflow: 'hidden', flexShrink: 0, backgroundColor: c.white },
  segBtn: { flex: 1, height: 44, alignItems: 'center', justifyContent: 'center' },
  segText: { fontFamily: font.semi, fontSize: 14, color: c.deep },
  search: { height: 48, minHeight: 48, borderWidth: 1, borderColor: c.input, borderRadius: 14, paddingLeft: 42, paddingRight: 14, backgroundColor: c.white, fontFamily: font.body, fontSize: 14, color: c.text, flexShrink: 0 },
  opt: { borderWidth: 1, borderColor: c.border, borderRadius: 12, padding: 12, backgroundColor: c.white },
  name: { fontFamily: font.semi, fontSize: 14, color: c.text },
  sub: { fontFamily: font.body, fontSize: 12, color: c.muted, marginTop: 4 },
  linked: { fontFamily: font.semi, fontSize: 11, color: c.primary, marginTop: 2 },
  smallBtn: { borderWidth: 1.5, borderColor: c.primary, borderRadius: 12, paddingVertical: 10, paddingHorizontal: 12, alignSelf: 'flex-start' },
  smallBtnText: { color: c.primary, fontFamily: font.bold, fontSize: 13 },
  big: { fontFamily: font.title, fontSize: 20, color: c.text },
  bar: { height: 8, borderRadius: 4, backgroundColor: '#E3EDF3', marginTop: 8 },
  barFill: { height: 8, borderRadius: 4, backgroundColor: '#0B8F5A' },
  h: { fontFamily: font.bold, fontSize: 11, letterSpacing: 0.6, color: c.muted },
  list: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 16, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 11, paddingHorizontal: 14 },
  rowLine: { borderBottomWidth: 1, borderBottomColor: '#E3EDF3' },
  event: { width: 62, fontFamily: font.bold, fontSize: 14, color: c.text },
  bold: { fontFamily: font.bold, color: c.text },
  time: { fontFamily: font.title, fontSize: 15, color: c.text },
  pill: { flexDirection: 'row', alignItems: 'center', gap: 4, borderRadius: 12, paddingVertical: 4, paddingHorizontal: 10 },
  pillText: { fontFamily: font.bold, fontSize: 12 },
});
