import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useFocusEffect, useLocalSearchParams } from 'expo-router';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { api, Item } from '../../api';
import { useAuth } from '../../auth';
import { dayLabel } from '../../fechas';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Avatar, Chip, ConfirmDialog, Empty, ErrorText, Header, Icon } from '../../ui';

type Group = { key: string; name: string; club: string | null; category: string | null; entries: Item[] };

/** Agrupa las inscripciones por nadador, en el orden en que nada cada uno por primera vez. */
function groupBySwimmer(rows: Item[]): Group[] {
  const map = new Map<string, Group>();
  for (const r of rows) {
    const key = r.swimmer_id ? `id:${r.swimmer_id}` : `n:${r.swimmer_name}|${r.club_code ?? ''}`;
    let g = map.get(key);
    if (!g) { g = { key, name: r.swimmer_name, club: r.club_code, category: r.category, entries: [] }; map.set(key, g); }
    g.entries.push(r);
  }
  return [...map.values()];
}

const MAX_ROWS = 200; // tope de tarjetas en pantalla (por prueba) o de nadadores (agrupado)

export default function Torneos() {
  const { can } = useAuth();
  const isAdmin = can('eliminar_programa');
  const [toDelete, setToDelete] = useState<Item | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [comps, setComps] = useState<Item[]>([]);
  const [open, setOpen] = useState<Item | null>(null);
  const [swimmer, setSwimmer] = useState('');
  const [mine, setMine] = useState(false);
  const [rows, setRows] = useState<Item[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [byPerson, setByPerson] = useState(true);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const groups = useMemo(() => groupBySwimmer(rows), [rows]);
  // Con pocos nadadores (o en Mis alertas) se ven abiertos; con muchos, cerrados para poder recorrer la lista.
  const openByDefault = mine || groups.length <= 3;
  const isOpen = (key: string) => expanded[key] ?? openByDefault;
  // Desde el Inicio (?comp=id): abre ese programa con las alertas de mis nadadores.
  const { comp: compParam } = useLocalSearchParams<{ comp?: string }>();
  const openedParam = useRef<string | null>(null);

  // Las pestañas quedan montadas: se recarga la lista cada vez que se abre Torneos
  // para que aparezca un programa recién cargado desde Admin.
  useFocusEffect(
    useCallback(() => {
      api('/competitions').then((r) => {
        setComps(r.items);
        const found = compParam && compParam !== openedParam.current ? r.items.find((x: Item) => String(x.id) === compParam) : null;
        if (found) { openedParam.current = compParam!; setOpen(found); setSwimmer(''); setMine(true); }
      }).catch((e) => setError(e.message)).finally(() => setLoading(false));
    }, [compParam]),
  );

  const load = useCallback(async (comp: Item, name: string, onlyMine: boolean) => {
    setLoading(true); setError(null);
    const p = new URLSearchParams();
    if (name.trim().length >= 3) p.set('swimmer', name.trim());
    try {
      // Alertas: inscripciones de mi nadador y de los que sigo.
      setRows((await api(onlyMine ? `/competitions/${comp.id}/alerts` : `/competitions/${comp.id}/schedule?${p}`)).items);
      setExpanded({});
    }
    catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  // Solo el administrador (el servidor también lo exige). Borra el programa y sus inscripciones.
  const remove = async () => {
    if (!toDelete) return;
    const comp = toDelete;
    setDeleting(true); setError(null); setMsg(null);
    try {
      await api(`/competitions/${comp.id}`, { method: 'DELETE' });
      setComps((list) => list.filter((x) => x.id !== comp.id));
      setMsg(`Programa eliminado: ${comp.name}`);
    } catch (e: any) { setError(e.message); }
    finally { setDeleting(false); setToDelete(null); }
  };

  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => load(open, swimmer, mine), 350);
    return () => clearTimeout(t);
  }, [open, swimmer, mine, load]);

  if (open) {
    return (
      <View style={s.root}>
        <Header title="Programa" subtitle={open.name} right={<ProfileButton />} />
        <View style={{ padding: 16, gap: 10, flex: 1 }}>
          <Pressable onPress={() => { setOpen(null); setSwimmer(''); setMine(false); setRows([]); }}><Text style={s.back}>← Campeonatos</Text></Pressable>
          <View style={{ flexDirection: 'row', gap: 8, flexShrink: 0 }}>
            <Chip label="Todos" selected={!mine} onPress={() => setMine(false)} />
            <Chip label="Mis alertas (nadadores que sigo)" selected={mine} onPress={() => setMine(true)} />
          </View>
          <TextInput value={swimmer} onChangeText={setSwimmer} editable={!mine} placeholder="Filtrar por nadador (mín. 3 letras)" placeholderTextColor="#8AA3B5" style={s.search} />
          <View accessibilityRole="tablist" style={s.segment}>
            {[{ v: true, label: 'Por nadador', icon: 'swimmer' }, { v: false, label: 'Por prueba', icon: 'list' }].map((o) => (
              <Pressable key={o.label} accessibilityRole="tab" accessibilityState={{ selected: byPerson === o.v }}
                onPress={() => setByPerson(o.v)} style={[s.segBtn, byPerson === o.v && s.segOn]}>
                <Icon name={o.icon} size={16} color={byPerson === o.v ? c.deep : c.muted} />
                <Text style={[s.segText, byPerson === o.v && { color: c.deep }]}>{o.label}</Text>
              </Pressable>
            ))}
          </View>
          {!loading && rows.length ? (
            <Text style={s.sub}>{groups.length} {groups.length === 1 ? 'nadador' : 'nadadores'} · {rows.length} {rows.length === 1 ? 'prueba' : 'pruebas'}</Text>
          ) : null}
          <ErrorText text={error} />
          {loading ? <ActivityIndicator color={c.primary} /> : byPerson ? (
            <FlatList
              data={groups.slice(0, MAX_ROWS)}
              keyExtractor={(g) => g.key}
              contentContainerStyle={{ gap: 10, paddingBottom: 16 }}
              ListEmptyComponent={<Empty text={mine ? 'Sin alertas: sigue nadadores desde su ficha.' : 'Sin inscripciones para ese filtro.'} />}
              renderItem={({ item: g }) => {
                const opened = isOpen(g.key);
                return (
                  <View style={s.group}>
                    <Pressable accessibilityRole="button" accessibilityState={{ expanded: opened }}
                      accessibilityLabel={`${g.name}, ${g.entries.length} ${g.entries.length === 1 ? 'prueba' : 'pruebas'}`}
                      onPress={() => setExpanded((e) => ({ ...e, [g.key]: !opened }))} style={s.groupHead}>
                      <Avatar label={g.name} size={38} />
                      <View style={{ flex: 1 }}>
                        <Text style={s.name}>{g.name}</Text>
                        <Text style={s.sub}>{[g.club, g.category].filter(Boolean).join(' · ')}</Text>
                      </View>
                      <Text style={s.count}>{g.entries.length} {g.entries.length === 1 ? 'prueba' : 'pruebas'}</Text>
                      <View style={{ transform: [{ rotate: opened ? '-90deg' : '90deg' }] }}><Icon name="chevron" size={18} /></View>
                    </Pressable>
                    {opened ? g.entries.map((e, i) => (
                      <View key={i} style={s.entry}>
                        <View style={{ width: 56, alignItems: 'center' }}>
                          <Text style={s.time}>{e.start_time ?? '—'}</Text>
                          <Text style={s.small}>{dayLabel(e.date)}</Text>
                        </View>
                        <View style={{ flex: 1 }}>
                          <Text style={s.event}>{e.event_label}</Text>
                          <Text style={s.sub}>Serie {e.heat} · Carril {e.lane}</Text>
                        </View>
                        {e.seed ? (
                          <View style={{ alignItems: 'flex-end' }}>
                            <Text style={s.seed}>{e.seed}</Text>
                            <Text style={s.small}>inscripción</Text>
                          </View>
                        ) : null}
                      </View>
                    )) : null}
                  </View>
                );
              }}
            />
          ) : (
            <FlatList
              data={rows.slice(0, MAX_ROWS)}
              keyExtractor={(_, i) => String(i)}
              contentContainerStyle={{ gap: 8, paddingBottom: 16 }}
              ListEmptyComponent={<Empty text={mine ? 'Sin alertas: sigue nadadores desde su ficha.' : 'Sin inscripciones para ese filtro.'} />}
              renderItem={({ item }) => (
                <View style={s.card}>
                  <Text style={s.name}>{item.swimmer_name} · {item.club_code}</Text>
                  <Text style={s.sub}>{item.event_label} · Serie {item.heat} · Carril {item.lane} · {dayLabel(item.date)} {item.start_time ?? ''}</Text>
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
      {msg ? <Text style={{ color: c.deep, fontFamily: font.semi, paddingHorizontal: 16, paddingTop: 12 }}>{msg}</Text> : null}
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
              {isAdmin ? (
                <Pressable onPress={() => setToDelete(item)} accessibilityRole="button" accessibilityLabel={`Eliminar ${item.name}`} hitSlop={8} style={s.del}>
                  <Text style={s.delText}>Eliminar programa</Text>
                </Pressable>
              ) : null}
            </Pressable>
          )}
        />
      )}
      <ConfirmDialog
        visible={!!toDelete}
        danger
        title="¿Eliminar este programa?"
        message={`${toDelete?.name ?? ''}\nSe borrarán sus ${toDelete?.entradas ?? 0} inscripciones y las alertas de seguimiento de todos los usuarios. No se puede deshacer; podrás volver a cargar el PDF desde Admin.`}
        confirmLabel={deleting ? 'Eliminando…' : 'Eliminar'}
        confirmDisabled={deleting}
        onConfirm={remove}
        onCancel={() => setToDelete(null)}
      />
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  back: { color: c.primary, fontFamily: font.semi },
  search: { height: 48, minHeight: 48, borderWidth: 1, borderColor: c.input, borderRadius: 14, paddingHorizontal: 14, backgroundColor: c.white, fontFamily: font.body, fontSize: 14, color: c.text, flexShrink: 0 },
  card: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 14, padding: 12 },
  name: { fontFamily: font.semi, color: c.text, fontSize: 14 },
  sub: { fontFamily: font.body, color: c.muted, fontSize: 12, marginTop: 2 },
  del: { alignSelf: 'flex-start', marginTop: 10, paddingVertical: 6, paddingHorizontal: 12, borderRadius: 10, borderWidth: 1, borderColor: c.danger },
  segment: { flexDirection: 'row', backgroundColor: '#E3EDF3', borderRadius: 12, padding: 3, gap: 3, flexShrink: 0 },
  segBtn: { flex: 1, height: 40, borderRadius: 10, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 },
  segOn: { backgroundColor: c.white, shadowColor: c.deep, shadowOpacity: 0.15, shadowRadius: 3, shadowOffset: { width: 0, height: 1 }, elevation: 1 },
  segText: { fontFamily: font.semi, fontSize: 13, color: c.muted },
  group: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 16, overflow: 'hidden' },
  groupHead: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 14, paddingVertical: 10, minHeight: 60 },
  count: { backgroundColor: c.chip, color: c.deep, borderRadius: 12, paddingHorizontal: 9, paddingVertical: 4, fontSize: 11, fontFamily: font.bold, overflow: 'hidden' },
  entry: { flexDirection: 'row', alignItems: 'center', gap: 12, paddingHorizontal: 14, paddingVertical: 10, borderTopWidth: 1, borderTopColor: '#E3EDF3' },
  time: { fontFamily: font.title, fontSize: 15, color: c.text },
  small: { fontFamily: font.body, fontSize: 10, color: c.muted },
  event: { fontFamily: font.semi, fontSize: 14, color: c.text },
  seed: { fontFamily: font.title, fontSize: 14, color: c.deep },
  delText: { color: c.danger, fontFamily: font.semi, fontSize: 12 },
});
