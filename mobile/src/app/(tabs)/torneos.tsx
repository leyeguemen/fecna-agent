import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { api, Item } from '../../api';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Empty, ErrorText, Header } from '../../ui';

export default function Torneos() {
  const [comps, setComps] = useState<Item[]>([]);
  const [open, setOpen] = useState<Item | null>(null);
  const [swimmer, setSwimmer] = useState('');
  const [rows, setRows] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api('/competitions').then((r) => setComps(r.items)).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);

  const load = useCallback(async (comp: Item, name: string) => {
    setLoading(true); setError(null);
    const p = new URLSearchParams();
    if (name.trim().length >= 3) p.set('swimmer', name.trim());
    try { setRows((await api(`/competitions/${comp.id}/schedule?${p}`)).items); }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => load(open, swimmer), 350);
    return () => clearTimeout(t);
  }, [open, swimmer, load]);

  if (open) {
    return (
      <View style={s.root}>
        <Header title="Programa" subtitle={open.name} right={<ProfileButton />} />
        <View style={{ padding: 16, gap: 10, flex: 1 }}>
          <Pressable onPress={() => { setOpen(null); setSwimmer(''); setRows([]); }}><Text style={s.back}>← Campeonatos</Text></Pressable>
          <TextInput value={swimmer} onChangeText={setSwimmer} placeholder="Filtrar por nadador (mín. 3 letras)" placeholderTextColor="#8AA3B5" style={s.search} />
          <ErrorText text={error} />
          {loading ? <ActivityIndicator color={c.primary} /> : (
            <FlatList
              data={rows.slice(0, 200)}
              keyExtractor={(_, i) => String(i)}
              contentContainerStyle={{ gap: 8 }}
              ListEmptyComponent={<Empty text="Sin inscripciones para ese filtro." />}
              renderItem={({ item }) => (
                <View style={s.card}>
                  <Text style={s.name}>{item.swimmer_name} · {item.club_code}</Text>
                  <Text style={s.sub}>{item.event_label} · Serie {item.heat} · Carril {item.lane} · {item.date} {item.start_time ?? ''}</Text>
                  {item.seed ? <Text style={s.sub}>Inscripción: {item.seed}</Text> : null}
                </View>
              )}
            />
          )}
        </View>
      </View>
    );
  }

  return (
    <View style={s.root}>
      <Header title="Campeonatos" subtitle="Programas publicados" right={<ProfileButton />} />
      <ErrorText text={error} />
      {loading ? <ActivityIndicator style={{ marginTop: 24 }} color={c.primary} /> : (
        <FlatList
          data={comps}
          keyExtractor={(i) => String(i.id)}
          contentContainerStyle={{ padding: 16, gap: 10 }}
          ListEmptyComponent={<Empty text="Aún no hay programas. El administrador puede cargarlos." />}
          renderItem={({ item }) => (
            <Pressable style={s.card} onPress={() => setOpen(item)}>
              <Text style={s.name}>{item.name}</Text>
              <Text style={s.sub}>{item.entradas} inscripciones · {item.pool_type ?? '—'}</Text>
            </Pressable>
          )}
        />
      )}
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  back: { color: c.primary, fontFamily: font.semi },
  search: { height: 48, borderWidth: 1, borderColor: c.input, borderRadius: 14, paddingHorizontal: 14, backgroundColor: c.white, fontFamily: font.body },
  card: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 14, padding: 12 },
  name: { fontFamily: font.semi, color: c.text, fontSize: 14 },
  sub: { fontFamily: font.body, color: c.muted, fontSize: 12, marginTop: 2 },
});
