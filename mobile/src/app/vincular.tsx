import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { api, Item } from '../api';
import { useAuth } from '../auth';
import { c, font } from '../theme';
import { Button, ErrorText, Field } from '../ui';

// Vincula la cuenta con un nadador. Se verifica con su fecha de nacimiento.
export default function Vincular() {
  const { first } = useLocalSearchParams<{ first?: string }>();
  const { clearPendingLink } = useAuth();
  const [q, setQ] = useState('');
  const [results, setResults] = useState<Item[]>([]);
  const [picked, setPicked] = useState<Item | null>(null);
  const [birth, setBirth] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const leave = () => { clearPendingLink(); if (first) router.replace('/'); else router.back(); };

  useEffect(() => {
    if (picked || q.trim().length < 3) { setResults([]); return; }
    const t = setTimeout(() => {
      api(`/swimmers/search?q=${encodeURIComponent(q.trim())}`).then((r) => setResults(r.items)).catch((e) => setError(e.message));
    }, 350);
    return () => clearTimeout(t);
  }, [q, picked]);

  const verify = async () => {
    setBusy(true); setError(null);
    try {
      await api('/me/swimmer', { method: 'PUT', body: { swimmer_id: picked!.swimmer_id, birth_date: birth.trim() } });
      leave();
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  return (
    <KeyboardAvoidingView style={s.root} behavior="padding">
      <ScrollView contentContainerStyle={{ padding: 24, paddingTop: 72, gap: 14 }} keyboardShouldPersistTaps="handled">
        <Text style={s.title}>¿Eres nadador?</Text>
        <Text style={s.sub}>Vincula tu ficha para verla al instante. Lo verificamos con tu fecha de nacimiento. Es opcional.</Text>
        {!picked ? (
          <>
            <Field label="Tu nombre" value={q} onChangeText={setQ} placeholder="Mínimo 3 letras" autoCapitalize="words" />
            {results.map((r) => (
              <Pressable key={r.swimmer_id} style={s.result} onPress={() => setPicked(r)}>
                <Text style={s.name}>{r.swimmer_name}</Text>
                <Text style={s.sub}>{[r.club, r.league].filter(Boolean).join(' · ')}</Text>
              </Pressable>
            ))}
          </>
        ) : (
          <>
            <View style={s.result}>
              <Text style={s.name}>{picked.swimmer_name}</Text>
              <Pressable onPress={() => { setPicked(null); setBirth(''); }}><Text style={s.link}>Cambiar</Text></Pressable>
            </View>
            <Field label="Fecha de nacimiento (AAAA-MM-DD)" value={birth} onChangeText={setBirth} placeholder="2009-03-25" keyboardType="numbers-and-punctuation" />
            <Button title="Verificar y vincular" onPress={verify} loading={busy} disabled={!/^\d{4}-\d{2}-\d{2}$/.test(birth.trim())} />
          </>
        )}
        <ErrorText text={error} />
        <Button title={first ? 'Omitir por ahora' : 'Cancelar'} variant="outline" onPress={leave} />
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  title: { fontFamily: font.title, fontSize: 28, color: c.deep },
  sub: { fontFamily: font.body, fontSize: 13, color: c.muted, lineHeight: 19 },
  result: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 14, padding: 12, gap: 2 },
  name: { fontFamily: font.semi, color: c.text, fontSize: 14 },
  link: { color: c.primary, fontFamily: font.semi, fontSize: 13 },
});
