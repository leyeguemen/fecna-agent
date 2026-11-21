import { useEffect, useRef, useState } from 'react';
import { FlatList, KeyboardAvoidingView, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { api } from '../../api';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Chip, Header, Icon } from '../../ui';

type Msg = { role: 'user' | 'assistant'; content: string; error?: boolean };

const SUGGESTIONS = [
  'Top 5 de 100 libre masculino piscina larga',
  'Mejor marca de…',
  'Comparar dos nadadores',
  'Evolución en 200 mariposa',
];

export default function Chat() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [slow, setSlow] = useState(false);
  const list = useRef<FlatList<Msg>>(null);

  useEffect(() => { list.current?.scrollToEnd({ animated: true }); }, [msgs, busy]);

  const send = async (q: string) => {
    q = q.trim();
    if (!q || busy) return;
    const history = msgs.filter((m) => !m.error).map(({ role, content }) => ({ role, content }));
    setMsgs((m) => [...m, { role: 'user', content: q }]);
    setText(''); setBusy(true); setSlow(false);
    const t = setTimeout(() => setSlow(true), 8000); // arranque en frío del servidor
    try {
      const r = await api<{ reply: string }>('/ask', { body: { question: q, history } });
      setMsgs((m) => [...m, { role: 'assistant', content: r.reply }]);
    } catch (e: any) {
      setMsgs((m) => [...m, { role: 'assistant', content: e.message, error: true }]);
    } finally {
      clearTimeout(t); setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView style={s.root} behavior="padding">
      <Header title="NATIA" subtitle="Tu asistente de natación" right={<ProfileButton />} />
      <FlatList
        ref={list}
        data={msgs}
        keyExtractor={(_, i) => String(i)}
        contentContainerStyle={{ padding: 16, gap: 12, flexGrow: 1 }}
        ListEmptyComponent={<Text style={s.hint}>Pregunta por rankings, mejores marcas o evolución de un nadador.</Text>}
        renderItem={({ item }) => (
          <View style={[s.bubble, item.role === 'user' ? s.user : s.bot, item.error && { borderColor: c.danger }]}>
            <Text selectable style={[s.msg, item.role === 'user' && { color: c.white }]}>{item.content}</Text>
          </View>
        )}
        ListFooterComponent={busy ? (
          <View style={[s.bubble, s.bot]}>
            <Text style={s.msg}>{slow ? 'Despertando el servidor, puede tardar hasta un minuto…' : '…'}</Text>
          </View>
        ) : undefined}
      />
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ flexGrow: 0, flexShrink: 0, height: 48 }} contentContainerStyle={{ gap: 8, paddingHorizontal: 16, alignItems: 'center' }}>
        {SUGGESTIONS.map((q) => <Chip key={q} label={q} onPress={() => (q.endsWith('…') ? setText(q.slice(0, -1) + ' ') : send(q))} />)}
      </ScrollView>
      <View style={s.bar}>
        <TextInput value={text} onChangeText={setText} placeholder="Pregunta sobre rankings y marcas"
          placeholderTextColor="#8AA3B5" style={s.input} onSubmitEditing={() => send(text)} returnKeyType="send" />
        <Pressable accessibilityLabel="Enviar" onPress={() => send(text)} disabled={busy || !text.trim()}
          style={[s.send, (busy || !text.trim()) && { opacity: 0.5 }]}>
          <Icon name="send" size={20} color={c.white} />
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  hint: { color: c.muted, fontFamily: font.body, textAlign: 'center', marginTop: 40 },
  bubble: { maxWidth: '88%', padding: 12, borderRadius: 16 },
  user: { alignSelf: 'flex-end', backgroundColor: c.primary, borderBottomRightRadius: 4 },
  bot: { alignSelf: 'flex-start', backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderBottomLeftRadius: 4 },
  msg: { fontFamily: font.body, fontSize: 14, lineHeight: 20, color: c.text },
  bar: { flexDirection: 'row', gap: 8, paddingHorizontal: 16, paddingBottom: 12, alignItems: 'center' },
  input: { flex: 1, height: 48, borderWidth: 1, borderColor: c.input, borderRadius: 24, paddingHorizontal: 18, fontSize: 14, fontFamily: font.body, backgroundColor: c.white, color: c.text },
  send: { width: 48, height: 48, borderRadius: 24, backgroundColor: c.primary, alignItems: 'center', justifyContent: 'center' },
});
