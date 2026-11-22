import * as DocumentPicker from 'expo-document-picker';
import { useCallback, useEffect, useState } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { api, Item } from '../../api';
import { useAuth } from '../../auth';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Button, Card, ConfirmDialog, ErrorText, Header } from '../../ui';

export default function Admin() {
  const { can } = useAuth();
  const canSync = can('sincronizar');
  const canUpload = can('cargar_programa');
  const [status, setStatus] = useState<Item | null>(null);
  const [confirmSync, setConfirmSync] = useState<null | 'incremental' | 'completa'>(null);
  const [pdf, setPdf] = useState<DocumentPicker.DocumentPickerAsset | null>(null);
  const [confirmPub, setConfirmPub] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [publishing, setPublishing] = useState(false);
  const busy = syncing || publishing;
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    if (!canSync) return;
    api('/admin/sync/status').then(setStatus).catch((e) => setError(e.message));
  }, [canSync]);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 20_000);
    return () => clearInterval(t);
  }, [refresh]);

  const sync = async () => {
    const modo = confirmSync;
    if (!modo) return;
    setConfirmSync(null); setSyncing(true); setError(null); setMsg(null);
    try {
      await api('/admin/sync', { body: { modo } });
      setMsg(modo === 'completa'
        ? 'Sincronización completa en cola. Puede tardar bastante; corre en segundo plano y puedes cerrar la app.'
        : 'Sincronización en cola. Corre en segundo plano; puedes cerrar la app.');
      setTimeout(refresh, 4000);
    } catch (e: any) { setError(e.message); }
    finally { setSyncing(false); }
  };

  const choose = async () => {
    const r = await DocumentPicker.getDocumentAsync({ type: 'application/pdf', copyToCacheDirectory: true });
    if (!r.canceled) { setPdf(r.assets[0]); setError(null); setMsg(null); }
  };

  const publish = async () => {
    if (!pdf) return;
    setConfirmPub(false); setPublishing(true); setError(null); setMsg(null);
    try {
      const form = new FormData();
      // En web el asset trae el File del navegador; en el teléfono se envía por URI.
      if (Platform.OS === 'web' && pdf.file) form.append('file', pdf.file, pdf.name);
      else form.append('file', { uri: pdf.uri, name: pdf.name, type: 'application/pdf' } as any);
      const r = await api('/competitions', { form });
      setMsg(`Programa publicado${r?.status ? ` (${r.status})` : ''}.`);
      setPdf(null);
    } catch (e: any) { setError(e.message); }
    finally { setPublishing(false); }
  };

  // Historial completo de un nadador, por demanda.
  const [hq, setHq] = useState('');
  const [hres, setHres] = useState<Item[]>([]);
  const [hsel, setHsel] = useState<Item | null>(null);
  const [hst, setHst] = useState<Item | null>(null);
  const [hbusy, setHbusy] = useState(false);

  useEffect(() => {
    if (!canSync || hq.trim().length < 3) { setHres([]); return; }
    const t = setTimeout(() => api(`/swimmers/search?q=${encodeURIComponent(hq.trim())}`).then((r) => setHres(r.items)).catch((e) => setError(e.message)), 350);
    return () => clearTimeout(t);
  }, [hq, canSync]);

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

  const run = status?.run;
  const last = status?.last_sync;

  return (
    <View style={s.root}>
      <Header title="Admin · Datos" subtitle="Sincronización y programas" right={<ProfileButton />} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }} keyboardShouldPersistTaps="handled">
        {canSync ? <Card>
          <Text style={s.h}>ESTADO</Text>
          <Text style={s.v}>{status ? `${status.total_results.toLocaleString('es-CO')} marcas` : 'Cargando…'}</Text>
          {status?.latest_result_date ? <Text style={s.sub}>Datos hasta: {status.latest_result_date}</Text> : null}
          <Text style={s.sub}>Última sincronización: {last ? `${new Date(last.run_at).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })} · ${last.inserted} nuevas` : 'sin registros'}</Text>
          {run ? <Text style={s.sub}>Ejecución: {run.status}{run.conclusion ? ` · ${run.conclusion}` : ''}</Text> : null}
        </Card> : null}

        {canSync ? <Card>
          <Text style={s.h}>SINCRONIZAR RANKING FECNA</Text>
          <Text style={[s.sub, { marginBottom: 12 }]}>
            Trae solo las novedades desde la última marca guardada, con un margen de 30 días por si FECNA publica resultados con retraso.
          </Text>
          <View style={{ gap: 12 }}>
            <Button title="Sincronizar ahora" onPress={() => setConfirmSync('incremental')} loading={syncing} disabled={busy} />
            <Button title="Sincronización completa" variant="outline" onPress={() => setConfirmSync('completa')} disabled={busy} />
          </View>
        </Card> : null}

        {canSync ? <Card>
          <Text style={s.h}>HISTORIAL COMPLETO DE UN NADADOR</Text>
          <Text style={[s.sub, { marginBottom: 10 }]}>Trae de FECNA todas sus marcas (todas las pruebas y años). Tarda hasta un minuto.</Text>
          <TextInput value={hq} onChangeText={setHq} placeholder="Buscar nadador (mín. 3 letras)" placeholderTextColor="#8AA3B5"
            autoCapitalize="none" style={s.search} />
          {hres.map((it) => (
            <Pressable key={it.swimmer_id} onPress={() => pickSwimmer(it)} style={s.opt} accessibilityRole="button">
              <Text style={s.optName} numberOfLines={1}>{it.swimmer_name}</Text>
              <Text style={s.sub} numberOfLines={1}>{[it.club, it.league].filter(Boolean).join(' · ')}</Text>
            </Pressable>
          ))}
          {hsel ? (
            <View style={{ marginTop: 12, gap: 10 }}>
              <Text style={s.optName}>{hsel.swimmer_name}</Text>
              {hst ? <Text style={s.sub}>
                {hst.ranking_marks} marcas del ranking · {hst.extra_marks} del historial · {hst.last_fetched
                  ? `última descarga ${new Date(hst.last_fetched).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })}` : 'sin descargar'}
              </Text> : null}
              <Button title={hbusy ? 'Trayendo historial…' : 'Traer historial completo'} onPress={fetchHistory} loading={hbusy} disabled={hbusy || !hst} />
            </View>
          ) : null}
        </Card> : null}

        {canUpload ? <Card>
          <Text style={s.h}>PROGRAMA DE CAMPEONATO (PDF)</Text>
          <View style={{ gap: 12, marginTop: 8 }}>
            <Button title={pdf ? pdf.name : 'Elegir PDF'} variant="outline" onPress={choose} disabled={busy} />
            <Button title="Publicar programa" onPress={() => setConfirmPub(true)} disabled={!pdf || busy} loading={publishing} />
            {publishing ? <Text style={s.sub}>Subiendo y leyendo el programa… puede tardar hasta un minuto. No cierres la app.</Text> : null}
          </View>
        </Card> : null}

        {msg ? <Text style={{ color: c.deep, fontFamily: font.semi }}>{msg}</Text> : null}
        <ErrorText text={error} />
      </ScrollView>

      <ConfirmDialog visible={confirmSync === 'incremental'} title="¿Sincronizar el ranking?" confirmLabel="Sincronizar"
        message="Se consultarán las novedades de FECNA desde la última actualización. Puede tardar varios minutos y se ejecuta en segundo plano; puedes cerrar la app."
        onConfirm={sync} onCancel={() => setConfirmSync(null)} />
      <ConfirmDialog visible={confirmSync === 'completa'} title="¿Sincronización completa?" confirmLabel="Sincronizar"
        message="Se vuelve a consultar todo el ranking de FECNA desde 2024. Es lenta (puede tardar más de una hora) y sirve para reparar huecos. Para el uso normal basta «Sincronizar ahora»."
        onConfirm={sync} onCancel={() => setConfirmSync(null)} />
      <ConfirmDialog visible={confirmPub} title="¿Publicar el programa?" confirmLabel="Publicar"
        message={`${pdf?.name ?? ''}. Será visible para todos los usuarios; si ya existe uno con el mismo nombre se reemplaza.`}
        onConfirm={publish} onCancel={() => setConfirmPub(false)} />
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  h: { fontFamily: font.bold, fontSize: 11, letterSpacing: 0.6, color: c.muted },
  v: { fontFamily: font.title, fontSize: 24, color: c.deep, marginTop: 4 },
  sub: { fontFamily: font.body, fontSize: 12, color: c.muted, marginTop: 4 },
  search: { height: 48, minHeight: 48, borderWidth: 1, borderColor: c.input, borderRadius: 14, paddingHorizontal: 14, backgroundColor: c.white, fontFamily: font.body, fontSize: 14, color: c.text, flexShrink: 0 },
  opt: { borderWidth: 1, borderColor: c.border, borderRadius: 12, padding: 10, backgroundColor: c.white, marginTop: 6 },
  optName: { fontFamily: font.semi, fontSize: 14, color: c.text },
});
