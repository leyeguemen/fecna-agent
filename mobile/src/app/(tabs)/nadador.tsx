import * as DocumentPicker from 'expo-document-picker';
import { File, Paths } from 'expo-file-system';
import { useLocalSearchParams } from 'expo-router';
import * as Sharing from 'expo-sharing';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Image, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import Svg, { Circle, Line, Polyline } from 'react-native-svg';
import { api, apiImage, Item } from '../../api';
import { useAuth } from '../../auth';
import { c, font } from '../../theme';
import { SOURCE_NOTE } from '../../legal';
import { Avatar, ConfirmDialog, Empty, ErrorText, Icon, SourceNote } from '../../ui';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const shortDate = (iso: string) => {
  const [y, m] = iso.split('-');
  return `${MESES[Number(m) - 1] ?? ''} ${y.slice(2)}`;
};
const shortEvent = (name: string) => name.split('/')[0].trim();

function spanText(first: string, last: string) {
  const days = (new Date(last).getTime() - new Date(first).getTime()) / 864e5;
  if (days >= 548) return `${Math.round(days / 365)} años`;
  if (days >= 45) return `${Math.round(days / 30)} meses`;
  return `${Math.max(1, Math.round(days))} días`;
}

// ---- Gráfica de evolución (mejor tiempo abajo, como en el diseño) ---------------
function Evolution({ points, width }: { points: Item[]; width: number }) {
  const H = 112, padX = 10, padY = 10;
  if (points.length < 2 || width <= 0) return <Empty text="Aún no hay suficientes marcas para graficar." />;
  const ms = points.map((p) => p.time_ms as number);
  const min = Math.min(...ms), max = Math.max(...ms), span = Math.max(max - min, 1);
  const xy = points.map((p, i) => [
    padX + (i * (width - 2 * padX)) / (points.length - 1),
    padY + ((p.time_ms - min) / span) * (H - 2 * padY) * -1 + (H - 2 * padY),
  ]);
  const mid = points[Math.floor(points.length / 2)];
  return (
    <View>
      <Svg width={width} height={H}>
        {[0.15, 0.5, 0.85].map((f) => (
          <Line key={f} x1={0} x2={width} y1={H * f} y2={H * f} stroke={c.border} strokeWidth={1} />
        ))}
        <Polyline points={xy.map((p) => p.join(',')).join(' ')} fill="none" stroke={c.primary} strokeWidth={2.5} strokeLinejoin="round" />
        {xy.map(([x, y], i) => (
          <Circle key={i} cx={x} cy={y} r={4.5} stroke={c.primary} strokeWidth={2.5} fill={i === xy.length - 1 ? c.primary : c.white} />
        ))}
      </Svg>
      <View style={s.axis}>
        <Text style={s.axisText}>{shortDate(points[0].date)}</Text>
        <Text style={s.axisText}>{shortDate(mid.date)}</Text>
        <Text style={s.axisText}>{shortDate(points[points.length - 1].date)}</Text>
      </View>
    </View>
  );
}

export default function Nadador() {
  const { can } = useAuth();
  const canCompare = can('comparar');
  const canShare = can('ficha_redes');
  const { id } = useLocalSearchParams<{ id?: string }>();
  const insets = useSafeAreaInsets();
  const [searching, setSearching] = useState(false);
  const [q, setQ] = useState('');
  const [results, setResults] = useState<Item[]>([]);
  const [profile, setProfile] = useState<Item | null>(null);
  const [selected, setSelected] = useState<Item | null>(null);
  const [history, setHistory] = useState<Item[]>([]);
  const [all, setAll] = useState<Item[]>([]);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({});
  const [following, setFollowing] = useState(false);
  const [cmpOpen, setCmpOpen] = useState(false);
  const [cmpQ, setCmpQ] = useState('');
  const [cmpResults, setCmpResults] = useState<Item[]>([]);
  const [cmp, setCmp] = useState<Item | null>(null);
  const [cmpRes, setCmpRes] = useState<Item | null>(null);
  const [chartW, setChartW] = useState(0);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [scope, setScope] = useState<string | null>(null); // campeonato elegido (null = mejores marcas)
  const [ficha, setFicha] = useState<{ uri: string; name: string; file?: any } | null>(null); // ficha ya generada
  const [photo, setPhoto] = useState<DocumentPicker.DocumentPickerAsset | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Historial de la prueba elegida.
  const loadHistory = useCallback(async (swimmerId: string, e: Item) => {
    setSelected(e); setHistory([]);
    const p = new URLSearchParams({ event_id: e.event_id, pool: e.pool });
    try { setHistory((await api(`/swimmers/${encodeURIComponent(swimmerId)}/history?${p}`)).items); }
    catch (err: any) { setError(err.message); }
  }, []);

  const open = useCallback(async (swimmerId: string) => {
    setLoading(true); setError(null); setCmp(null); setCmpRes(null); setCmpQ(''); setCmpOpen(false); setSearching(false);
    try {
      const p = await api(`/swimmers/${encodeURIComponent(swimmerId)}`);
      setProfile(p); setAll([]); setOpenGroups({});
      api(`/swimmers/${encodeURIComponent(swimmerId)}/history`).then((h) => setAll(h.items)).catch(() => {});
      const me = await api('/me');
      setFollowing(me.following.some((f: Item) => f.swimmer_id === swimmerId));
      // Prueba destacada: la mejor posición nacional.
      const best = [...p.top_events].sort((a: Item, b: Item) => a.national_rank - b.national_rank)[0];
      if (best) await loadHistory(swimmerId, best); else { setSelected(null); setHistory([]); }
    } catch (e: any) { setError(e.message); }
    finally { setLoading(false); }
  }, [loadHistory]);

  // Abre el nadador indicado, o "mi nadador" si la cuenta lo tiene vinculado.
  useEffect(() => {
    if (id) { open(id); return; }
    api('/me').then((me) => { if (me.swimmer && !profile) open(me.swimmer.swimmer_id); else if (!me.swimmer) setSearching(true); }).catch(() => setSearching(true));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (q.trim().length < 3) { setResults([]); return; }
    const t = setTimeout(() => {
      api(`/swimmers/search?q=${encodeURIComponent(q.trim())}`).then((r) => setResults(r.items)).catch((e) => setError(e.message));
    }, 350);
    return () => clearTimeout(t);
  }, [q]);

  useEffect(() => {
    if (cmpQ.trim().length < 3 || cmp) { setCmpResults([]); return; }
    const t = setTimeout(() => {
      api(`/swimmers/search?q=${encodeURIComponent(cmpQ.trim())}`).then((r) => setCmpResults(r.items)).catch((e) => setError(e.message));
    }, 350);
    return () => clearTimeout(t);
  }, [cmpQ, cmp]);

  useEffect(() => {
    if (!cmp || !selected || !profile) { setCmpRes(null); return; }
    const p = new URLSearchParams({ a: profile.swimmer_id, b: cmp.swimmer_id, event_id: selected.event_id, pool: selected.pool });
    api(`/swimmers/compare?${p}`).then(setCmpRes).catch((e) => setError(e.message));
  }, [cmp, selected, profile]);

  const toggleFollow = async () => {
    try { await api(`/me/following/${encodeURIComponent(profile!.swimmer_id)}`, { method: following ? 'DELETE' : 'PUT' }); setFollowing(!following); }
    catch (err: any) { setError(err.message); }
  };

  // Campeonatos en los que hay marcas con torneo conocido (solo nadadores seguidos), el más reciente primero.
  const tournaments = useMemo(() => {
    const last = new Map<string, string>();
    for (const h of all) if (h.tournament && (last.get(h.tournament) ?? '') < h.date) last.set(h.tournament, h.date);
    return [...last.entries()].sort((x, y) => (x[1] < y[1] ? 1 : -1)).map(([name]) => name);
  }, [all]);

  const pickPhoto = async () => {
    const r = await DocumentPicker.getDocumentAsync({ type: 'image/*', copyToCacheDirectory: true });
    if (!r.canceled) setPhoto(r.assets[0]);
  };

  // Genera la ficha 9:16 en el servidor y la comparte: hoja de compartir en el teléfono; en la web,
  // compartir del sistema si existe o descarga del archivo.
  const shareFicha = async () => {
    if (!profile) return;
    setShareOpen(false); setBusy(true); setError(null);
    try {
      const form = new FormData();
      if (scope) form.append('tournament', scope);
      if (photo) {
        if (Platform.OS === 'web' && photo.file) form.append('photo', photo.file, photo.name);
        else form.append('photo', { uri: photo.uri, name: photo.name || 'foto.jpg', type: photo.mimeType || 'image/jpeg' } as any);
      }
      const bytes = await apiImage(`/swimmers/${encodeURIComponent(profile.swimmer_id)}/ficha-redes`, form);
      const name = `ficha-${profile.swimmer_name.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.png`;
      if (Platform.OS === 'web') {
        const file = new (globalThis as any).File([bytes], name, { type: 'image/png' });
        setFicha({ uri: URL.createObjectURL(file), name, file });
      } else {
        const file = new File(Paths.cache, name);
        file.create({ overwrite: true });
        file.write(new Uint8Array(bytes));
        setFicha({ uri: file.uri, name });
      }
    } catch (e: any) { setError(e.message || 'No se pudo generar la ficha.'); }
    finally { setBusy(false); }
  };

  // Compartir/descargar la ficha ya generada. Va en un toque aparte porque los navegadores (iPhone)
  // solo permiten "compartir" justo después de un toque del usuario, no tras esperar al servidor.
  const shareReady = async () => {
    if (!ficha) return;
    setError(null);
    try {
      if (Platform.OS === 'web') {
        const nav: any = navigator;
        if (nav.canShare?.({ files: [ficha.file] })) await nav.share({ files: [ficha.file], title: 'Ficha NATIA' });
        else downloadReady();
      } else if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(ficha.uri, { mimeType: 'image/png', UTI: 'public.png', dialogTitle: 'Compartir ficha' });
      } else setError('Este dispositivo no permite compartir archivos.');
    } catch (e: any) {
      if (e?.name !== 'AbortError') setError(e?.message || 'No se pudo compartir la ficha.');
    }
  };

  const downloadReady = () => {
    if (!ficha || Platform.OS !== 'web') return;
    const a = document.createElement('a');
    a.href = ficha.uri; a.download = ficha.name; document.body.appendChild(a); a.click(); a.remove();
  };

  const stats = useMemo(() => {
    if (!selected) return null;
    const pts = history.map((h) => h.points).filter((x) => typeof x === 'number');
    const delta = history.length >= 2 ? history[history.length - 1].time_ms - history[0].time_ms : null;
    return {
      best: selected.best_time as string,
      sub: `${shortEvent(selected.event_name)} · ${selected.pool}`,
      points: pts.length ? Math.max(...pts) : null,
      rank: selected.national_rank as number,
      delta,
      span: history.length >= 2 ? spanText(history[0].date, history[history.length - 1].date) : '',
    };
  }, [selected, history]);

  // Todas las marcas agrupadas por prueba/piscina: orden cronológico para calcular el cambio
  // frente a la marca anterior; se muestran de la más reciente a la más antigua.
  const groups = useMemo(() => {
    const map = new Map<string, Item[]>();
    for (const h of all) {
      const k = `${h.event_id}|${h.pool}`;
      map.set(k, [...(map.get(k) ?? []), h]);
    }
    return [...map.entries()].map(([key, rows]) => {
      let best = Infinity;
      const marks: Item[] = rows.map((r, i) => {
        const pb = r.time_ms < best;
        best = Math.min(best, r.time_ms);
        return { ...r, pb, diff: i > 0 ? r.time_ms - rows[i - 1].time_ms : null };
      }).reverse();
      return { key, name: shortEvent(rows[0].event_name), pool: rows[0].pool as string, marks, best: Math.min(...rows.map((r) => r.time_ms)) };
    }).sort((a, b) => b.marks.length - a.marks.length);
  }, [all]);

  const sub = profile ? [profile.club, profile.league, profile.gender, profile.age != null ? `${profile.age} años` : null].filter(Boolean).join(' · ') : 'Ficha, posiciones y evolución';

  return (
    <View style={s.root}>
      <View style={[s.header, { paddingTop: (Platform.OS === 'web' ? 0 : insets.top) + 14 }]}>
        {profile ? <Avatar label={profile.swimmer_name} size={56} /> : null}
        <View style={{ flex: 1 }}>
          <Text style={s.name} numberOfLines={1}>{profile ? profile.swimmer_name : 'Nadador'}</Text>
          <Text style={s.subtitle} numberOfLines={2}>{sub}</Text>
        </View>
      </View>

      <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }} keyboardShouldPersistTaps="handled">
        {profile ? (
          <View style={{ flexDirection: 'row', gap: 8 }}>
            <Pressable onPress={toggleFollow} style={[s.action, following && { backgroundColor: c.chip, borderColor: c.accent }]}>
              <Text style={s.actionText}>{following ? '✓ Siguiendo' : '+ Seguir'}</Text>
            </Pressable>
            <Pressable accessibilityLabel="Buscar otro nadador" onPress={() => setSearching((v) => !v)} style={[s.action, { flexDirection: 'row', gap: 6 }]}>
              <Icon name="search" size={14} color={c.primary} />
              <Text style={s.actionText}>Buscar otro</Text>
            </Pressable>
          </View>
        ) : null}
        {searching ? (
          <View style={{ gap: 8 }}>
            <TextInput autoFocus value={q} onChangeText={setQ} placeholder="Buscar por nombre (mín. 3 letras)" placeholderTextColor="#8AA3B5" style={s.search} />
            {results.map((r) => (
              <Pressable key={r.swimmer_id} style={s.row} onPress={() => { setQ(''); setResults([]); open(r.swimmer_id); }}>
                <View style={{ flex: 1 }}>
                  <Text style={s.rowName}>{r.swimmer_name}</Text>
                  <Text style={s.small}>{[r.club, r.league].filter(Boolean).join(' · ')}</Text>
                </View>
              </Pressable>
            ))}
          </View>
        ) : null}
        <ErrorText text={error} />
        {loading ? <ActivityIndicator color={c.primary} style={{ marginTop: 24 }} /> : null}

        {profile && !loading ? (
          <>
            {stats ? (
              <>
                <View style={{ flexDirection: 'row', gap: 12 }}>
                  <View style={[s.card, { flex: 1 }]}>
                    <Text style={s.small}>Mejor marca</Text>
                    <Text style={s.big}>{stats.best}</Text>
                    <Text style={s.small} numberOfLines={1}>{stats.sub}</Text>
                  </View>
                  <View style={[s.card, { flex: 1 }]}>
                    <Text style={s.small}>Puntos WA</Text>
                    <Text style={s.big}>{stats.points ?? '—'}</Text>
                    <Text style={s.small}>Ranking nac. #{stats.rank}</Text>
                  </View>
                </View>

                <View style={s.card} onLayout={(e) => setChartW(e.nativeEvent.layout.width - 28)}>
                  <View style={s.cardHead}>
                    <Text style={s.cardTitle} numberOfLines={1}>Evolución · {shortEvent(selected!.event_name)}</Text>
                    {stats.delta != null ? (
                      <View style={s.chip}>
                        <Text style={s.chipText}>{stats.delta <= 0 ? '−' : '+'}{(Math.abs(stats.delta) / 1000).toFixed(2)} s en {stats.span}</Text>
                      </View>
                    ) : null}
                  </View>
                  <Evolution points={history} width={chartW} />
                </View>
              </>
            ) : null}

            {canCompare || canShare ? (
              <View style={{ flexDirection: 'row', gap: 12 }}>
                {canCompare ? (
                  <Pressable style={[s.btn, s.btnPrimary]} onPress={() => setCmpOpen((v) => !v)}>
                    <Text style={[s.btnText, { color: c.white }]}>Comparar con…</Text>
                  </Pressable>
                ) : null}
                {canShare ? (
                  <Pressable style={[s.btn, s.btnOutline, busy && { opacity: 0.6 }]} onPress={() => setShareOpen(true)} disabled={busy}>
                    {busy ? <ActivityIndicator color={c.primary} /> : <Text style={[s.btnText, { color: c.primary }]}>Ficha para redes</Text>}
                  </Pressable>
                ) : null}
              </View>
            ) : null}

            {cmpOpen && canCompare ? (
              <View style={s.card}>
                {!selected ? <Text style={s.small}>Elige primero una prueba.</Text> : !cmp ? (
                  <>
                    <Text style={s.cardTitle}>Comparar en {shortEvent(selected.event_name)} · {selected.pool}</Text>
                    <TextInput value={cmpQ} onChangeText={setCmpQ} placeholder="Nombre del otro nadador" placeholderTextColor="#8AA3B5" style={[s.search, { marginTop: 8 }]} />
                    {cmpResults.map((r) => (
                      <Pressable key={r.swimmer_id} style={[s.row, { marginTop: 8 }]} onPress={() => { setCmp(r); setCmpResults([]); }}>
                        <Text style={s.rowName}>{r.swimmer_name}</Text>
                      </Pressable>
                    ))}
                  </>
                ) : (
                  <View style={{ gap: 6 }}>
                    <Text style={s.cardTitle}>Comparar en {shortEvent(selected.event_name)} · {selected.pool}</Text>
                    {cmpRes ? (
                      <>
                        <Text style={s.rowName}>{cmpRes.a?.swimmer_name ?? profile.swimmer_name}: {cmpRes.a?.time ?? 'sin marca'}</Text>
                        <Text style={s.rowName}>{cmpRes.b?.swimmer_name ?? cmp.swimmer_name}: {cmpRes.b?.time ?? 'sin marca'}</Text>
                        <Text style={s.small}>{cmpRes.diff ? `Diferencia: ${cmpRes.diff}` : 'No hay marcas de ambos en esta prueba.'}</Text>
                      </>
                    ) : null}
                    <Pressable onPress={() => { setCmp(null); setCmpRes(null); setCmpQ(''); }}><Text style={s.link}>Cambiar rival</Text></Pressable>
                  </View>
                )}
              </View>
            ) : null}

            <Text style={s.section}>Mejores marcas por prueba</Text>
            {profile.top_events.map((e: Item) => {
              const on = selected?.event_id === e.event_id && selected?.pool === e.pool;
              return (
                <Pressable key={`${e.event_id}-${e.pool}`} onPress={() => loadHistory(profile.swimmer_id, e)} style={[s.event, on && { borderColor: c.primary }]}>
                  <Text style={s.rowName}>{shortEvent(e.event_name)}{e.pool === 'SC' ? ' · corta' : ''}</Text>
                  <Text style={s.eventTime}>{e.best_time}</Text>
                </Pressable>
              );
            })}

            {groups.length ? (
              <>
                <Text style={s.section}>Todas las marcas · {all.length}</Text>
                {groups.map((g) => {
                  const isOpen = openGroups[g.key] ?? (selected ? `${selected.event_id}|${selected.pool}` === g.key : false);
                  return (
                    <View key={g.key} style={s.card}>
                      <Pressable onPress={() => setOpenGroups((o) => ({ ...o, [g.key]: !isOpen }))} style={s.groupHead}>
                        <View style={{ flex: 1 }}>
                          <Text style={s.rowName}>{g.name}{g.pool === 'SC' ? ' · corta' : ''}</Text>
                          <Text style={s.small}>{g.marks.length} {g.marks.length === 1 ? 'marca' : 'marcas'} · mejor {g.marks.find((m) => m.time_ms === g.best)?.time}</Text>
                        </View>
                        <Text style={s.link}>{isOpen ? 'Ocultar' : 'Ver'}</Text>
                      </Pressable>
                      {isOpen ? g.marks.map((m, i) => (
                        <View key={i} style={s.markRow}>
                          <Text style={[s.small, { width: 64 }]}>{shortDate(m.date)}</Text>
                          <View style={{ flex: 1 }}>
                            <Text style={s.eventTime}>{m.time}{m.pb ? ' ★' : ''}</Text>
                            {m.tournament ? <Text style={s.small} numberOfLines={2}>{m.tournament}</Text> : null}
                          </View>
                          <Text style={[s.small, { color: m.diff == null ? c.muted : m.diff <= 0 ? '#1B8A4B' : '#C0392B' }]}>
                            {m.diff == null ? 'primera' : `${m.diff <= 0 ? '−' : '+'}${(Math.abs(m.diff) / 1000).toFixed(2)}`}
                          </Text>
                        </View>
                      )) : null}
                    </View>
                  );
                })}
                <Text style={s.small}>★ = mejor marca hasta esa fecha. El cambio es frente a la marca anterior en la misma prueba.</Text>
              </>
            ) : null}
            <SourceNote text={SOURCE_NOTE} />
          </>
        ) : null}

        <ConfirmDialog
          visible={shareOpen}
          title="Ficha para redes"
          message="Imagen vertical lista para WhatsApp, historias e Instagram. Elige qué mostrar y, si quieres, agrega una foto."
          confirmLabel="Generar y compartir"
          onConfirm={shareFicha}
          onCancel={() => setShareOpen(false)}
        >
          <Text style={[s.small, { marginTop: 14, marginBottom: 6 }]}>Marcas a mostrar</Text>
          <ScrollView style={{ maxHeight: 190 }}>
            {[null, ...tournaments].map((t) => (
              <Pressable key={t ?? 'all'} onPress={() => setScope(t)} style={[s.row, { marginBottom: 6 }, scope === t && { borderColor: c.primary, borderWidth: 1.5 }]}>
                <Text style={[s.rowName, { flex: 1 }]} numberOfLines={2}>{t ?? 'Mis mejores marcas (todas)'}</Text>
              </Pressable>
            ))}
          </ScrollView>
          {!tournaments.length ? <Text style={s.small}>Sigue al nadador para elegir por campeonato.</Text> : null}
          <Pressable onPress={pickPhoto} style={[s.row, { marginTop: 8 }]}>
            <Text style={[s.rowName, { flex: 1 }]} numberOfLines={1}>{photo ? `Foto: ${photo.name}` : 'Agregar foto (opcional)'}</Text>
            {photo ? <Pressable onPress={() => setPhoto(null)} accessibilityLabel="Quitar foto"><Text style={s.link}>Quitar</Text></Pressable> : null}
          </Pressable>
          <Text style={[s.small, { marginTop: 6 }]}>La foto solo se usa para armar la imagen; no se guarda en NATIA.</Text>
        </ConfirmDialog>

        <ConfirmDialog
          visible={!!ficha}
          title="Tu ficha está lista"
          message={Platform.OS === 'web' ? 'Pulsa Compartir, o Descargar para guardarla. En el iPhone también puedes mantener presionada la imagen.' : 'Pulsa Compartir para enviarla o guardarla.'}
          confirmLabel="Compartir"
          onConfirm={shareReady}
          onCancel={() => setFicha(null)}
        >
          {ficha ? <Image source={{ uri: ficha.uri }} style={{ width: 216, height: 384, alignSelf: 'center', marginTop: 12, borderRadius: 12, backgroundColor: c.chip }} resizeMode="contain" accessibilityLabel="Vista previa de la ficha" /> : null}
          {Platform.OS === 'web' ? <Pressable onPress={downloadReady} style={{ marginTop: 10, alignSelf: 'center' }}><Text style={s.link}>Descargar imagen</Text></Pressable> : null}
          <ErrorText text={error} />
        </ConfirmDialog>

        {!profile && !loading && !searching ? <Empty text="Busca un nadador o abre uno desde el Ranking." /> : null}
      </ScrollView>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  header: { backgroundColor: c.deep, paddingHorizontal: 16, paddingBottom: 16, flexDirection: 'row', alignItems: 'center', gap: 12 },
  name: { color: c.white, fontFamily: font.title, fontSize: 20 },
  subtitle: { color: c.headerSub, fontFamily: font.body, fontSize: 12, marginTop: 2 },
  action: { alignItems: 'center', justifyContent: 'center', borderWidth: 1.5, borderColor: c.border, borderRadius: 16, paddingHorizontal: 12, paddingVertical: 7, backgroundColor: c.white },
  actionText: { color: c.primary, fontFamily: font.semi, fontSize: 12 },
  search: { height: 48, minHeight: 48, borderWidth: 1, borderColor: c.input, borderRadius: 14, paddingHorizontal: 14, backgroundColor: c.white, fontFamily: font.body, fontSize: 14, color: c.text, flexShrink: 0 },
  card: { backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 16, padding: 14, gap: 2 },
  cardHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10, gap: 8 },
  cardTitle: { fontFamily: font.bold, fontSize: 14, color: c.text, flexShrink: 1 },
  chip: { backgroundColor: c.chip, borderRadius: 12, paddingHorizontal: 10, paddingVertical: 4 },
  chipText: { color: c.deep, fontFamily: font.semi, fontSize: 11 },
  big: { fontFamily: font.title, fontSize: 26, color: c.text, marginVertical: 2 },
  small: { fontFamily: font.body, color: c.muted, fontSize: 12 },
  axis: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 6, paddingHorizontal: 4 },
  axisText: { fontFamily: font.body, color: c.muted, fontSize: 11 },
  btn: { flex: 1, height: 52, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  btnPrimary: { backgroundColor: c.primary },
  btnOutline: { backgroundColor: c.white, borderWidth: 1.5, borderColor: c.primary },
  btnText: { fontFamily: font.bold, fontSize: 14 },
  section: { fontFamily: font.bold, fontSize: 14, color: c.text, marginTop: 6 },
  event: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: c.white, borderWidth: 1.5, borderColor: c.border, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 14 },
  eventTime: { fontFamily: font.bold, fontSize: 15, color: c.text },
  groupHead: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  markRow: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingTop: 10, marginTop: 8, borderTopWidth: 1, borderTopColor: c.border },
  row: { flexDirection: 'row', alignItems: 'center', backgroundColor: c.white, borderWidth: 1, borderColor: c.border, borderRadius: 14, padding: 12 },
  rowName: { fontFamily: font.semi, color: c.text, fontSize: 14 },
  link: { color: c.primary, fontFamily: font.semi, fontSize: 13 },
});
