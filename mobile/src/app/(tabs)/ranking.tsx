import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { api, Item } from '../../api';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { SOURCE_NOTE } from '../../legal';
import { Chip, Empty, ErrorText, Header, SourceNote } from '../../ui';

export default function Ranking() {
  const [cat, setCat] = useState<{ pruebas: Item[]; categorias: Item[]; ligas: string[] } | null>(null);
  const [event, setEvent] = useState<Item | null>(null);
  const [pool, setPool] = useState<'LC' | 'SC'>('LC');
  const [gender, setGender] = useState<'M' | 'F'>('M');
  const [category, setCategory] = useState<string | null>(null);
  const [items, setItems] = useState<Item[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [picker, setPicker] = useState(false);
  const [q, setQ] = useState('');
  const [league, setLeague] = useState<string | null>(null);
  const [leaguePicker, setLeaguePicker] = useState(false);
  const [ql, setQl] = useState('');

  useEffect(() => {
    api('/catalogs').then((r) => { setCat(r); setEvent(r.pruebas[0] ?? null); }).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!event) return;
    setLoading(true); setError(null);
    const p = new URLSearchParams({ event_id: event.id, pool, gender, limit: '50' });
    if (category) p.set('category', category);
    if (league) p.set('league', league);
    api(`/rankings?${p}`).then((r) => setItems(r.items)).catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, [event, pool, gender, category, league]);

  const ligas = (cat?.ligas ?? []).filter((l) => l.toLowerCase().includes(ql.toLowerCase()));
  const pruebas = (cat?.pruebas ?? []).filter((p) => p.nombre.toLowerCase().includes(q.toLowerCase()));

  return (
    <View style={s.root}>
      <Header title="Ranking" subtitle={event?.nombre ?? 'Cargando…'} right={<ProfileButton />} />
      <View style={s.filters}>
        <Pressable style={s.select} onPress={() => setPicker(true)}>
          <Text style={s.selectText} numberOfLines={1}>{event?.nombre ?? 'Prueba'}</Text>
        </Pressable>
        <Pressable style={s.select} onPress={() => setLeaguePicker(true)}>
          <Text style={s.selectText} numberOfLines={1}>Liga: {league ?? 'Todas'}</Text>
        </Pressable>
        <View style={s.row}>
          <Chip label="Piscina larga" selected={pool === 'LC'} onPress={() => setPool('LC')} />
          <Chip label="Corta" selected={pool === 'SC'} onPress={() => setPool('SC')} />
          <Chip label="Masculino" selected={gender === 'M'} onPress={() => setGender('M')} />
          <Chip label="Femenino" selected={gender === 'F'} onPress={() => setGender('F')} />
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.row}>
          <Chip label="Todas" selected={!category} onPress={() => setCategory(null)} />
          {(cat?.categorias ?? []).map((k) => (
            <Chip key={k.id} label={k.nombre} selected={category === k.id} onPress={() => setCategory(k.id)} />
          ))}
        </ScrollView>
      </View>
      <ErrorText text={error} />
      {loading ? <ActivityIndicator style={{ marginTop: 24 }} color={c.primary} /> : (
        <FlatList
          data={items}
          keyExtractor={(i) => `${i.swimmer_id}-${i.pos}`}
          contentContainerStyle={{ padding: 16, gap: 8 }}
          ListEmptyComponent={<Empty text="Sin resultados con estos filtros." />}
          ListFooterComponent={<SourceNote text={SOURCE_NOTE} />}
          renderItem={({ item }) => (
            <Pressable style={s.item} onPress={() => router.push({ pathname: '/nadador', params: { id: item.swimmer_id } })}>
              <Text style={s.pos}>{item.pos}</Text>
              <View style={{ flex: 1 }}>
                <Text style={s.name} numberOfLines={1}>{item.swimmer_name}</Text>
                <Text style={s.sub} numberOfLines={1}>{[item.club, item.league].filter(Boolean).join(' · ')}</Text>
              </View>
              <Text style={s.time}>{item.time}</Text>
            </Pressable>
          )}
        />
      )}
      <Modal visible={picker} animationType="slide" onRequestClose={() => setPicker(false)}>
        <View style={[s.root, { paddingTop: 56 }]}>
          <TextInput value={q} onChangeText={setQ} placeholder="Buscar prueba" placeholderTextColor="#8AA3B5" style={s.search} />
          <FlatList
            data={pruebas}
            keyExtractor={(p) => p.id}
            renderItem={({ item }) => (
              <Pressable style={s.opt} onPress={() => { setEvent(item); setPicker(false); setQ(''); }}>
                <Text style={[s.name, item.id === event?.id && { color: c.primary }]}>{item.nombre}</Text>
              </Pressable>
            )}
          />
          <Pressable style={s.close} onPress={() => setPicker(false)}><Text style={s.closeText}>Cerrar</Text></Pressable>
        </View>
      </Modal>
      <Modal visible={leaguePicker} animationType="slide" onRequestClose={() => setLeaguePicker(false)}>
        <View style={[s.root, { paddingTop: 56 }]}>
          <TextInput value={ql} onChangeText={setQl} placeholder="Buscar liga" placeholderTextColor="#8AA3B5" style={s.search} />
          <FlatList
            data={['Todas', ...ligas]}
            keyExtractor={(l) => l}
            renderItem={({ item }) => {
              const value = item === 'Todas' ? null : item;
              return (
                <Pressable style={s.opt} onPress={() => { setLeague(value); setLeaguePicker(false); setQl(''); }}>
                  <Text style={[s.name, value === league && { color: c.primary }]}>{item}</Text>
                </Pressable>
              );
            }}
          />
          <Pressable style={s.close} onPress={() => setLeaguePicker(false)}><Text style={s.closeText}>Cerrar</Text></Pressable>
        </View>
      </Modal>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  filters: { padding: 16, gap: 10 },
  row: { flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  select: { height: 48, borderWidth: 1, borderColor: c.input, borderRadius: 14, backgroundColor: c.white, justifyContent: 'center', paddingHorizontal: 14 },
  selectText: { fontFamily: font.semi, color: c.text, fontSize: 14 },
  item: { flexDirection: 'row', alignItems: 'center', gap: 10, backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 14, padding: 12 },
  pos: { width: 26, fontFamily: font.bold, color: c.primary, fontSize: 15 },
  name: { fontFamily: font.semi, color: c.text, fontSize: 14 },
  sub: { fontFamily: font.body, color: c.muted, fontSize: 12, marginTop: 2 },
  time: { fontFamily: font.bold, color: c.deep, fontSize: 15 },
  search: { margin: 16, height: 48, borderWidth: 1, borderColor: c.input, borderRadius: 14, paddingHorizontal: 14, backgroundColor: c.white, fontFamily: font.body, fontSize: 14, color: c.text, flexShrink: 0 },
  opt: { paddingHorizontal: 20, paddingVertical: 14, borderBottomWidth: 1, borderBottomColor: c.border },
  close: { height: 56, alignItems: 'center', justifyContent: 'center' },
  closeText: { color: c.primary, fontFamily: font.bold },
});
