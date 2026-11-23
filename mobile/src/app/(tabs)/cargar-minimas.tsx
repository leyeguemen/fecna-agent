import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { api, Item } from '../../api';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Button, Card, Chip, ErrorText, Header } from '../../ui';

// Las tablas del reglamento vienen como imagen y no se pueden leer de forma fiable: las del reglamento 2026
// ya están cargadas y aquí el admin corrige cualquier tiempo (o las carga de nuevo cuando salga otro reglamento).
export default function CargarMinimas() {
  const [tournaments, setTournaments] = useState<Item[]>([]);
  const [tournament, setTournament] = useState('interligas');
  const [category, setCategory] = useState('juvb');
  const [gender, setGender] = useState<'M' | 'F'>('M');
  const [rows, setRows] = useState<Item[]>([]);
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api('/minimas/torneos').then((r) => setTournaments(r.items)).catch((e) => setError(e.message)); }, []);
  const cats: Item[] = tournaments.find((t) => t.id === tournament)?.categories ?? [];
  useEffect(() => { if (cats.length && !cats.some((x) => x.id === category)) setCategory(cats[0].id); }, [tournament, tournaments]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!cats.some((x) => x.id === category)) return;
    setMsg(null); setError(null);
    api(`/minimas/tabla?tournament=${tournament}&category=${category}&gender=${gender}`).then((r) => {
      setRows(r.rows);
      setValues(Object.fromEntries(r.rows.map((x: Item) => [x.event_id, x.minima])));
    }).catch((e) => setError(e.message));
  }, [tournament, category, gender, tournaments]); // eslint-disable-line react-hooks/exhaustive-deps

  const changed = rows.filter((r) => (values[r.event_id] ?? '') !== r.minima).length;

  const save = async () => {
    setSaving(true); setError(null); setMsg(null);
    try {
      const r = await api(`/minimas/${tournament}/${category}/${gender}`, { method: 'PUT', body: { marks: values } });
      setMsg(`Guardado: ${r.saved} marcas.`);
      const t = await api(`/minimas/tabla?tournament=${tournament}&category=${category}&gender=${gender}`);
      setRows(t.rows);
    } catch (e: any) { setError(e.message); }
    finally { setSaving(false); }
  };

  return (
    <View style={s.root}>
      <Header title="Marcas mínimas" subtitle="Corregir las del reglamento" onBack={() => router.replace('/config')} right={<ProfileButton />} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }} keyboardShouldPersistTaps="handled">
        <Card>
          <Text style={s.sub}>Las marcas del reglamento 2026 ya están cargadas. Elige el campeonato, la categoría y el género, y corrige los tiempos que hagan falta (formato mm:ss,cc).</Text>
        </Card>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ flexGrow: 0 }} contentContainerStyle={{ gap: 8 }}>
          {tournaments.map((t) => <Chip key={t.id} label={t.label} selected={tournament === t.id} onPress={() => setTournament(t.id)} />)}
        </ScrollView>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ flexGrow: 0 }} contentContainerStyle={{ gap: 8 }}>
          {cats.map((x) => <Chip key={x.id} label={x.label} selected={category === x.id} onPress={() => setCategory(x.id)} />)}
        </ScrollView>
        <View style={{ flexDirection: 'row', gap: 8 }}>
          <Chip label="Masculino" selected={gender === 'M'} onPress={() => setGender('M')} />
          <Chip label="Femenino" selected={gender === 'F'} onPress={() => setGender('F')} />
        </View>
        <View style={s.list}>
          {rows.map((r, i) => {
            const edited = (values[r.event_id] ?? '') !== r.minima;
            return (
              <View key={r.event_id} style={[s.row, i < rows.length - 1 && s.line]}>
                <Text style={s.event}>{r.event}</Text>
                <TextInput value={values[r.event_id] ?? ''} onChangeText={(t) => setValues({ ...values, [r.event_id]: t })}
                  accessibilityLabel={`Marca mínima ${r.event}`} placeholder="mm:ss,cc" placeholderTextColor="#8AA3B5" autoCapitalize="none"
                  style={[s.input, edited && { borderColor: '#D98A00', backgroundColor: '#FFF8EC' }]} />
              </View>
            );
          })}
        </View>
        {msg ? <Text style={{ color: c.deep, fontFamily: font.semi }}>{msg}</Text> : null}
        <ErrorText text={error} />
        <Button title={changed ? `Guardar cambios (${changed})` : 'Guardar'} onPress={save} loading={saving} disabled={!changed || saving} />
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  sub: { fontFamily: font.body, fontSize: 12, color: c.muted, lineHeight: 18 },
  list: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 16, overflow: 'hidden' },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 8, paddingHorizontal: 14 },
  line: { borderBottomWidth: 1, borderBottomColor: '#E3EDF3' },
  event: { width: 62, fontFamily: font.bold, fontSize: 14, color: c.text },
  input: { flex: 1, height: 44, borderWidth: 1, borderColor: c.input, borderRadius: 10, paddingHorizontal: 12, fontFamily: font.body, fontSize: 14, color: c.text, backgroundColor: c.white },
});
