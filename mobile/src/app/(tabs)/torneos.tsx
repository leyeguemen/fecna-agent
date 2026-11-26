import { useCallback, useMemo, useRef, useState } from 'react';
import { useFocusEffect, useLocalSearchParams } from 'expo-router';
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, TextInput, View } from 'react-native';
import { api, Item } from '../../api';
import { useAuth } from '../../auth';
import { dayLabel } from '../../fechas';
import { ProfileButton } from '../../ProfileButton';
import { PruebaDetalle } from '../../PruebaDetalle';
import { c, font } from '../../theme';
import { Avatar, ConfirmDialog, Empty, ErrorText, Header, Icon } from '../../ui';

type Group = { key: string; name: string; club: string | null; category: string | null; entries: Item[] };
type Row = { type: 'title'; key: string; text: string; mine: boolean } | { type: 'group'; key: string; g: Group; mine: boolean };

const swimmerKey = (r: Item) => (r.swimmer_id ? `id:${r.swimmer_id}` : `n:${r.swimmer_name}|${r.club_code ?? ''}`);
/** Minúsculas y sin tildes, para filtrar «Estupiñán» con «estupinan». */
const norm = (t: string) => t.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();

/** Agrupa las inscripciones por nadador, en el orden en que nada cada uno por primera vez. */
function groupBySwimmer(rows: Item[]): Group[] {
  const map = new Map<string, Group>();
  for (const r of rows) {
    const key = swimmerKey(r);
    let g = map.get(key);
    if (!g) { g = { key, name: r.swimmer_name, club: r.club_code, category: r.category, entries: [] }; map.set(key, g); }
    g.entries.push(r);
  }
  return [...map.values()];
}

const MAX_ROWS = 200; // tope de nadadores en pantalla (sin filtro); el buscador llega al resto

export default function Torneos() {
  const { can } = useAuth();
  const isAdmin = can('eliminar_programa');
  const [toDelete, setToDelete] = useState<Item | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [comps, setComps] = useState<Item[]>([]);
  const [open, setOpen] = useState<Item | null>(null);
  const [swimmer, setSwimmer] = useState('');
  const [rows, setRows] = useState<Item[]>([]);
  const [mineKeys, setMineKeys] = useState<Set<string>>(new Set()); // mi nadador, seguidos y vigilados
  const [loading, setLoading] = useState(true); // lista de campeonatos
  const [progLoading, setProgLoading] = useState(false); // inscripciones del programa abierto
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});
  const [detail, setDetail] = useState<{ entry: Item; mine: boolean } | null>(null); // prueba abierta
  const closeDetail = useCallback(() => setDetail(null), []);
  const groups = useMemo(() => groupBySwimmer(rows), [rows]);

  // Una sola lista: mis nadadores arriba y luego el resto. El filtro (nombre o club) aplica a las dos.
  const q = swimmer.trim();
  const filtered = useMemo(() => {
    const n = norm(q);
    return q.length < 3 ? groups : groups.filter((g) => norm(`${g.name} ${g.club ?? ''}`).includes(n));
  }, [groups, q]);
  const mineGroups = filtered.filter((g) => mineKeys.has(g.key));
  const others = filtered.filter((g) => !mineKeys.has(g.key));
  const shown = others.slice(0, MAX_ROWS);
  const entries = filtered.reduce((n, g) => n + g.entries.length, 0);
  // Mis nadadores se ven abiertos; el resto, cerrado salvo que queden pocos.
  const isOpen = (key: string, mine: boolean) => expanded[key] ?? (mine || others.length <= 3);
  const list: Row[] = [
    ...(mineGroups.length ? [{ type: 'title' as const, key: 't-mine', text: `TUS NADADORES · ${mineGroups.length}`, mine: true }] : []),
    ...mineGroups.map((g) => ({ type: 'group' as const, key: g.key, g, mine: true })),
    ...(shown.length ? [{ type: 'title' as const, key: 't-all', text: `${mineGroups.length ? 'TODOS LOS NADADORES' : 'NADADORES'} · ${others.length}`, mine: false }] : []),
    ...shown.map((g) => ({ type: 'group' as const, key: g.key, g, mine: false })),
  ];
  // Programa completo + alertas (inscripciones de mi nadador, de los que sigo y de los vigilados):
  // las alertas solo marcan quiénes van en «Tus nadadores». El filtro corre en el teléfono.
  const load = useCallback(async (comp: Item) => {
    setProgLoading(true); setError(null);
    try {
      const [all, alerts] = await Promise.all([
        api(`/competitions/${comp.id}/schedule`),
        api(`/competitions/${comp.id}/alerts`).catch(() => ({ items: [] })),
      ]);
      setRows(all.items);
      setMineKeys(new Set(alerts.items.map(swimmerKey)));
      setExpanded({});
    }
    catch (e: any) { setError(e.message); }
    finally { setProgLoading(false); }
  }, []);

  // Abre un programa y carga sus inscripciones.
  const openComp = useCallback((comp: Item) => { setOpen(comp); setSwimmer(''); setDetail(null); load(comp); }, [load]);
  // Desde el Inicio (?comp=id): abre ese programa (mis nadadores quedan arriba).
  const { comp: compParam } = useLocalSearchParams<{ comp?: string }>();
  const openedParam = useRef<string | null>(null);

  // Las pestañas quedan montadas: se recarga la lista cada vez que se abre Torneos
  // para que aparezca un programa recién cargado desde Admin.
  useFocusEffect(
    useCallback(() => {
      api('/competitions').then((r) => {
        setComps(r.items);
        const found = compParam && compParam !== openedParam.current ? r.items.find((x: Item) => String(x.id) === compParam) : null;
        if (found) { openedParam.current = compParam!; openComp(found); }
      }).catch((e) => setError(e.message)).finally(() => setLoading(false));
    }, [compParam, openComp]),
  );


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

  if (open) {
    return (
      <View style={s.root}>
        <Header title="Programa" subtitle={open.name} right={<ProfileButton />} />
        <View style={{ padding: 16, gap: 10, flex: 1 }}>
          <Pressable onPress={() => { setOpen(null); setSwimmer(''); setRows([]); setMineKeys(new Set()); setDetail(null); }}><Text style={s.back}>← Campeonatos</Text></Pressable>
          <View style={s.searchBox}>
            <Icon name="search" size={18} />
            <TextInput value={swimmer} onChangeText={setSwimmer} placeholder="Buscar nadador o club" placeholderTextColor="#8AA3B5"
              accessibilityLabel="Buscar nadador o club" style={s.searchInput} />
            {swimmer ? (
              <Pressable onPress={() => setSwimmer('')} accessibilityRole="button" accessibilityLabel="Borrar filtro" hitSlop={8} style={s.clear}>
                <Text style={{ color: c.muted, fontSize: 13 }}>✕</Text>
              </Pressable>
            ) : null}
          </View>
          {!progLoading && groups.length ? (
            <Text style={s.sub}>
              {q.length >= 3
                ? `${filtered.length} ${filtered.length === 1 ? 'coincide' : 'coinciden'} · ${entries} ${entries === 1 ? 'prueba' : 'pruebas'}`
                : `${groups.length} ${groups.length === 1 ? 'nadador' : 'nadadores'} · ${rows.length} ${rows.length === 1 ? 'prueba' : 'pruebas'}`}
            </Text>
          ) : null}
          <ErrorText text={error} />
          {progLoading ? <ActivityIndicator color={c.primary} /> : (
            <FlatList
              data={list}
              keyExtractor={(r) => r.key}
              keyboardShouldPersistTaps="handled"
              contentContainerStyle={{ gap: 10, paddingBottom: 16 }}
              ListEmptyComponent={<Empty text={q.length >= 3 ? `Nadie coincide con «${q}».` : 'Este programa no tiene inscripciones.'} />}
              ListFooterComponent={others.length > MAX_ROWS
                ? <Text style={[s.sub, { textAlign: 'center' }]}>Se muestran {MAX_ROWS} de {others.length}. Usa el buscador para ver el resto.</Text>
                : undefined}
              renderItem={({ item: r }) => {
                if (r.type === 'title') {
                  return (
                    <View style={[s.titleRow, !r.mine && { marginTop: 6 }]}>
                      {r.mine ? <Text style={{ color: c.accent, fontSize: 13 }}>★</Text> : null}
                      <Text style={[s.overline, r.mine && { color: c.deep }]}>{r.text}</Text>
                    </View>
                  );
                }
                const { g, mine } = r;
                const opened = isOpen(g.key, mine);
                return (
                  <View style={[s.group, mine && { borderColor: '#9EDCEB' }]}>
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
                      <Pressable key={i} style={s.entry} onPress={() => setDetail({ entry: e, mine })}
                        accessibilityRole="button" accessibilityLabel={`Ver detalle: ${e.event_label}`}>
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
                        <Icon name="chevron" size={16} color="#8AA3B5" />
                      </Pressable>
                    )) : null}
                  </View>
                );
              }}
            />
          )}
        </View>
        {/* Encima del programa (no lo reemplaza): al volver se conserva el scroll y lo abierto. */}
        {detail ? (
          <View style={StyleSheet.absoluteFill}>
            <PruebaDetalle entry={detail.entry} mine={detail.mine} rows={rows} compName={open.name}
              pool={open.pool_type} onBack={closeDetail} />
          </View>
        ) : null}
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
            <Pressable style={s.card} onPress={() => openComp(item)}>
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
  card: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 14, padding: 12 },
  name: { fontFamily: font.semi, color: c.text, fontSize: 14 },
  sub: { fontFamily: font.body, color: c.muted, fontSize: 12, marginTop: 2 },
  del: { alignSelf: 'flex-start', marginTop: 10, paddingVertical: 6, paddingHorizontal: 12, borderRadius: 10, borderWidth: 1, borderColor: c.danger },
  searchBox: { height: 48, flexDirection: 'row', alignItems: 'center', gap: 8, borderWidth: 1, borderColor: c.input, borderRadius: 14, paddingHorizontal: 12, backgroundColor: c.white, flexShrink: 0 },
  searchInput: { flex: 1, height: '100%', fontFamily: font.body, fontSize: 14, color: c.text },
  clear: { width: 28, height: 28, borderRadius: 14, backgroundColor: '#E3EDF3', alignItems: 'center', justifyContent: 'center' },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  overline: { fontFamily: font.semi, fontSize: 12, color: c.muted, letterSpacing: 0.4 },
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
