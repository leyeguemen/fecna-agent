import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { ActivityIndicator, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { api, Item } from '../../api';
import { useAuth } from '../../auth';
import { ProfileButton } from '../../ProfileButton';
import { when } from '../../fechas';
import { c, font } from '../../theme';
import { Avatar, Button, ErrorText, Header, Icon } from '../../ui';

// Inicio: la primera pantalla al entrar. Resume lo del nadador vinculado y de los que sigue,
// y lleva a cada sección. Cada tarjeta sale solo si el rol tiene el permiso (el servidor igual filtra).

function greeting() {
  const h = new Date().getHours();
  return h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches';
}

export default function Inicio() {
  const { can } = useAuth();
  const [data, setData] = useState<Item | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState('');

  useFocusEffect(useCallback(() => {
    api('/me/home').then((r) => { setData(r); setError(null); }).catch((e) => setError(e.message));
  }, []));

  const ask = (text: string) => {
    const t = text.trim();
    if (!t) return;
    setQ('');
    router.push({ pathname: '/chat', params: { q: t } });
  };

  const sw = data?.swimmer;
  const comp = data?.next_competition;
  const minima = data?.minima;
  const top = sw?.top_event;
  const w = when(comp?.first?.date);
  const progress = minima?.best_ms && minima?.minima_ms ? Math.min(1, minima.minima_ms / minima.best_ms) : null;

  return (
    <View style={s.root}>
      <Header title={greeting()} subtitle={sw ? 'Esto es lo nuevo de tus nadadores' : 'Tu asistente de natación'} right={<ProfileButton />} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
        <ErrorText text={error} />
        {!data && !error ? <ActivityIndicator style={{ marginTop: 24 }} color={c.primary} /> : null}

        {data && sw ? (
          <Pressable style={s.card} accessibilityRole="button" accessibilityLabel={`Ver la ficha de ${sw.swimmer_name}`}
            onPress={() => router.push({ pathname: '/nadador', params: { id: sw.swimmer_id } })}>
            <View style={s.row}>
              <Avatar label={sw.swimmer_name} size={44} />
              <View style={{ flex: 1 }}>
                <Text style={s.h}>MI NADADOR</Text>
                <Text style={s.title}>{sw.swimmer_name}</Text>
                <Text style={s.sub}>{[sw.club, sw.gender, sw.age ? `${sw.age} años` : null].filter(Boolean).join(' · ')}</Text>
              </View>
              <Icon name="chevron" size={18} />
            </View>
            {top ? (
              <View style={s.stats}>
                <View style={s.stat}>
                  <Text style={s.statLabel}>Mejor marca · {top.event_name}</Text>
                  <Text style={s.statValue}>{top.best_time ?? '—'}</Text>
                  <Text style={s.statNote}>Piscina {top.pool === 'LC' ? 'larga' : 'corta'}</Text>
                </View>
                <View style={s.stat}>
                  <Text style={s.statLabel}>Ranking nacional</Text>
                  <Text style={s.statValue}>{top.national_rank}.º</Text>
                  <Text style={s.statNote}>de {top.national_total} en su categoría</Text>
                </View>
              </View>
            ) : null}
          </Pressable>
        ) : null}

        {data && !sw && can('ver_nadador') ? (
          <View style={s.card}>
            <View style={s.iconBox}><Icon name="swimmer" size={22} color={c.primary} /></View>
            <Text style={[s.title, { marginTop: 10 }]}>Vincula a tu nadador</Text>
            <Text style={[s.sub, { lineHeight: 18, marginTop: 4, marginBottom: 12 }]}>
              Verás aquí sus marcas, su próximo torneo y cuánto le falta para las mínimas.
            </Text>
            <Button title="Vincular mi nadador" onPress={() => router.push('/vincular')} />
          </View>
        ) : null}

        {comp && w ? (
          <Pressable style={[s.card, { borderColor: c.primary }]} accessibilityRole="button" accessibilityLabel={`Ver el programa de ${comp.name}`}
            onPress={() => router.push({ pathname: '/torneos', params: { comp: String(comp.id) } })}>
            <View style={[s.row, { alignItems: 'flex-start' }]}>
              <View style={{ flex: 1 }}>
                <Text style={s.h}>PRÓXIMO TORNEO</Text>
                <Text style={s.title}>{comp.name}</Text>
              </View>
              <Text style={s.badge}>{w.left}</Text>
            </View>
            <View style={[s.row, s.inner]}>
              <View style={{ width: 64, alignItems: 'center' }}>
                <Text style={s.time}>{comp.first.start_time ?? '—'}</Text>
                <Text style={s.statNote}>{w.day}</Text>
              </View>
              <View style={{ flex: 1 }}>
                <Text style={s.event}>{comp.first.event_label}</Text>
                <Text style={s.sub}>{comp.first.swimmer_name} · Serie {comp.first.heat} · Carril {comp.first.lane}</Text>
              </View>
            </View>
            <View style={[s.row, { justifyContent: 'space-between' }]}>
              <Text style={s.sub}>{comp.entries} {comp.entries === 1 ? 'prueba' : 'pruebas'} de {comp.swimmers === 1 ? 'tu nadador' : `${comp.swimmers} nadadores`}</Text>
              <Text style={s.link}>Ver programa</Text>
            </View>
          </Pressable>
        ) : null}

        {data && !comp && can('ver_torneos') && data.competitions ? (
          <Pressable style={[s.card, s.row]} accessibilityRole="button" onPress={() => router.push('/torneos')}>
            <View style={s.iconBox}><Icon name="calendar" size={20} color={c.primary} /></View>
            <View style={{ flex: 1 }}>
              <Text style={s.event}>{data.competitions} {data.competitions === 1 ? 'programa publicado' : 'programas publicados'}</Text>
              <Text style={s.sub}>Mira series y carriles de cada torneo</Text>
            </View>
            <Icon name="chevron" size={18} />
          </Pressable>
        ) : null}

        {minima ? (
          <Pressable style={s.card} accessibilityRole="button" onPress={() => router.push('/minimas')}>
            {minima.event ? (
              <>
                <View style={[s.row, { justifyContent: 'space-between' }]}>
                  <Text style={[s.h, { flex: 1 }]}>MÍNIMA {minima.tournament_label.toUpperCase()} · {minima.event.toUpperCase()}</Text>
                  <Text style={s.missing}>Faltan {minima.diff}</Text>
                </View>
                {progress != null ? (
                  <View style={s.track} accessibilityLabel={`${Math.round(progress * 100)} % de la mínima`}>
                    <View style={[s.fill, { width: `${Math.round(progress * 100)}%` }]} />
                  </View>
                ) : null}
                <Text style={s.sub}>Marca {minima.best} · mínima {minima.minima} · cumple {minima.met} de {minima.total}</Text>
              </>
            ) : (
              <>
                <Text style={s.h}>MÍNIMAS {minima.tournament_label.toUpperCase()} · {minima.category_label}</Text>
                <Text style={[s.event, { marginTop: 4 }]}>Cumple {minima.met} de {minima.total} mínimas</Text>
              </>
            )}
          </Pressable>
        ) : null}

        {can('chat') ? (
          <>
            <Text style={[s.h, { marginTop: 4 }]}>PREGÚNTALE A NATIA</Text>
            <View style={s.askBar}>
              <TextInput value={q} onChangeText={setQ} placeholder="Escribe tu pregunta…" placeholderTextColor="#8AA3B5"
                style={s.askInput} onSubmitEditing={() => ask(q)} returnKeyType="send" />
              <Pressable accessibilityLabel="Preguntar" onPress={() => ask(q)} style={[s.send, !q.trim() && { opacity: 0.5 }]} disabled={!q.trim()}>
                <Icon name="send" size={18} color={c.white} />
              </Pressable>
            </View>
            {sw && top ? (
              <View style={s.chips}>
                {[`¿Cómo va ${sw.swimmer_name.split(' ')[0]} en ${top.event_name}?`, `Top 10 de ${top.event_name}`].map((t) => (
                  <Pressable key={t} onPress={() => ask(t)} style={s.chip}><Text style={s.chipText}>{t}</Text></Pressable>
                ))}
              </View>
            ) : null}
          </>
        ) : null}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  card: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 18, padding: 14, gap: 12 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  h: { fontFamily: font.bold, fontSize: 11, letterSpacing: 0.6, color: c.muted },
  title: { fontFamily: font.bold, fontSize: 16, color: c.text, marginTop: 1 },
  sub: { fontFamily: font.body, fontSize: 12, color: c.muted },
  stats: { flexDirection: 'row', gap: 8 },
  stat: { flex: 1, backgroundColor: c.bg, borderRadius: 12, padding: 10 },
  statLabel: { fontFamily: font.body, fontSize: 11, color: c.muted },
  statValue: { fontFamily: font.title, fontSize: 20, color: c.deep, marginTop: 2 },
  statNote: { fontFamily: font.body, fontSize: 11, color: c.muted },
  badge: { backgroundColor: c.chip, color: c.deep, borderRadius: 12, paddingHorizontal: 9, paddingVertical: 4, fontSize: 11, fontFamily: font.bold, overflow: 'hidden' },
  inner: { backgroundColor: c.bg, borderRadius: 12, padding: 10 },
  time: { fontFamily: font.title, fontSize: 15, color: c.text },
  event: { fontFamily: font.semi, fontSize: 14, color: c.text },
  link: { fontFamily: font.bold, fontSize: 13, color: c.primary },
  iconBox: { width: 40, height: 40, borderRadius: 12, backgroundColor: c.chip, alignItems: 'center', justifyContent: 'center' },
  missing: { fontFamily: font.bold, fontSize: 12, color: '#8A5A00' },
  track: { height: 8, borderRadius: 4, backgroundColor: '#E3EDF3', overflow: 'hidden' },
  fill: { height: 8, borderRadius: 4, backgroundColor: c.primary },
  askBar: { flexDirection: 'row', alignItems: 'center', gap: 8, height: 48, borderWidth: 1, borderColor: c.input, borderRadius: 24, backgroundColor: c.white, paddingLeft: 16, paddingRight: 6 },
  askInput: { flex: 1, fontFamily: font.body, fontSize: 14, color: c.text, height: 46 },
  send: { width: 36, height: 36, borderRadius: 18, backgroundColor: c.primary, alignItems: 'center', justifyContent: 'center' },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: { backgroundColor: c.chip, borderRadius: 16, paddingHorizontal: 12, minHeight: 36, justifyContent: 'center' },
  chipText: { color: c.deep, fontFamily: font.semi, fontSize: 12 },
});
