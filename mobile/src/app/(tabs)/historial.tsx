import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { api, Item } from '../../api';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Button, Card, ErrorText, Header } from '../../ui';

export default function Historial() {
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Historial completo de un nadador, por demanda.
  const [hq, setHq] = useState('');
  const [hres, setHres] = useState<Item[]>([]);
  const [hsel, setHsel] = useState<Item | null>(null);
  const [hst, setHst] = useState<Item | null>(null);
  const [hbusy, setHbusy] = useState(false);

  useEffect(() => {
    if (hq.trim().length < 3) { setHres([]); return; }
    const t = setTimeout(() => api(`/swimmers/search?q=${encodeURIComponent(hq.trim())}`).then((r) => setHres(r.items)).catch((e) => setError(e.message)), 350);
    return () => clearTimeout(t);
  }, [hq]);

  const pickSwimmer = (it: Item) => {
    setHsel(it); setHres([]); setHq(''); setHst(null); setError(null); setMsg(null);
    api(`/admin/swimmers/${encodeURIComponent(it.swimmer_id)}/historial`).then(setHst).catch((e) => setError(e.message));
  };

  const fetchHistory = async () => {
    if (!hsel) return;
    const before = hst?.extra_marks ?? 0;
    setHbusy(true); setError(null); setMsg(null);
    try {
      await api(`/admin/swimmers/${encodeURIComponent(hsel.swimmer_id)}/historial`, { method: 'POST' });
      // FECNA tarda hasta ~1 min: se consulta el estado hasta que cambie la hora de descarga o se agote la espera.
      const prev = hst?.last_fetched ?? null;
      for (let i = 0; i < 18; i++) {
        await new Promise((r) => setTimeout(r, 5000));
        const st = await api(`/admin/swimmers/${encodeURIComponent(hsel.swimmer_id)}/historial`);
        setHst(st);
        if (st.last_fetched && st.last_fetched !== prev) {
          setMsg(`Historial actualizado: ${st.extra_marks - before} marcas nuevas.`);
          return;
        }
      }
      setMsg('Sigue trabajando en segundo plano. Vuelve a elegir al nadador en un momento para ver el resultado.');
    } catch (e: any) { setError(e.message); }
    finally { setHbusy(false); }
  };

  return (
    <View style={s.root}>
      <Header title="Historial de un nadador" subtitle="Todas sus marcas, bajo demanda" onBack={() => router.replace('/config')} right={<ProfileButton />} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }} keyboardShouldPersistTaps="handled">
        <Card>
          <Text style={[s.sub, { marginBottom: 10 }]}>Trae de FECNA todas sus marcas (todas las pruebas y años). Tarda hasta un minuto.</Text>
          <TextInput value={hq} onChangeText={setHq} placeholder="Buscar nadador (mín. 3 letras)" placeholderTextColor="#8AA3B5"
            autoCapitalize="none" style={s.search} />
          {hres.map((it) => (
            <Pressable key={it.swimmer_id} onPress={() => pickSwimmer(it)} style={s.opt} accessibilityRole="button">
              <Text style={s.optName} numberOfLines={1}>{it.swimmer_name}</Text>
              <Text style={s.sub} numberOfLines={1}>{[it.club, it.league].filter(Boolean).join(' · ')}</Text>
            </Pressable>
          ))}
        </Card>
        {hsel ? (
          <Card>
            <Text style={s.h}>SELECCIONADO</Text>
            <View style={{ marginTop: 8, gap: 10 }}>
              <Text style={s.optName}>{hsel.swimmer_name}</Text>
              {hst ? <Text style={s.sub}>
                {hst.ranking_marks} marcas del ranking · {hst.extra_marks} del historial · {hst.last_fetched
                  ? `última descarga ${new Date(hst.last_fetched).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })}` : 'sin descargar'}
              </Text> : null}
              <Button title={hbusy ? 'Trayendo historial…' : 'Traer historial completo'} onPress={fetchHistory} loading={hbusy} disabled={hbusy || !hst} />
            </View>
          </Card>
        ) : null}
        {msg ? <Text style={{ color: c.deep, fontFamily: font.semi }}>{msg}</Text> : null}
        <ErrorText text={error} />
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  h: { fontFamily: font.bold, fontSize: 11, letterSpacing: 0.6, color: c.muted },
  sub: { fontFamily: font.body, fontSize: 12, color: c.muted, marginTop: 4 },
  search: { height: 48, minHeight: 48, borderWidth: 1, borderColor: c.input, borderRadius: 14, paddingHorizontal: 14, backgroundColor: c.white, fontFamily: font.body, fontSize: 14, color: c.text, flexShrink: 0 },
  opt: { borderWidth: 1, borderColor: c.border, borderRadius: 12, padding: 10, backgroundColor: c.white, marginTop: 6 },
  optName: { fontFamily: font.semi, fontSize: 14, color: c.text },
});
