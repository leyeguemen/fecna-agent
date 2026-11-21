import * as DocumentPicker from 'expo-document-picker';
import { useCallback, useEffect, useState } from 'react';
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { api, Item } from '../../api';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Button, Card, ConfirmDialog, ErrorText, Header } from '../../ui';

export default function Admin() {
  const [status, setStatus] = useState<Item | null>(null);
  const [confirmSync, setConfirmSync] = useState<null | 'incremental' | 'completa'>(null);
  const [pdf, setPdf] = useState<DocumentPicker.DocumentPickerAsset | null>(null);
  const [confirmPub, setConfirmPub] = useState(false);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api('/admin/sync/status').then(setStatus).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 20_000);
    return () => clearInterval(t);
  }, [refresh]);

  const sync = async () => {
    const modo = confirmSync;
    if (!modo) return;
    setConfirmSync(null); setBusy(true); setError(null); setMsg(null);
    try {
      await api('/admin/sync', { body: { modo } });
      setMsg(modo === 'completa'
        ? 'Sincronización completa en cola. Puede tardar bastante; corre en segundo plano y puedes cerrar la app.'
        : 'Sincronización en cola. Corre en segundo plano; puedes cerrar la app.');
      setTimeout(refresh, 4000);
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  const choose = async () => {
    const r = await DocumentPicker.getDocumentAsync({ type: 'application/pdf', copyToCacheDirectory: true });
    if (!r.canceled) { setPdf(r.assets[0]); setError(null); setMsg(null); }
  };

  const publish = async () => {
    if (!pdf) return;
    setConfirmPub(false); setBusy(true); setError(null); setMsg(null);
    try {
      const form = new FormData();
      // En web el asset trae el File del navegador; en el teléfono se envía por URI.
      if (Platform.OS === 'web' && pdf.file) form.append('file', pdf.file, pdf.name);
      else form.append('file', { uri: pdf.uri, name: pdf.name, type: 'application/pdf' } as any);
      const r = await api('/competitions', { form });
      setMsg(`Programa publicado${r?.status ? ` (${r.status})` : ''}.`);
      setPdf(null);
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  const run = status?.run;
  const last = status?.last_sync;

  return (
    <View style={s.root}>
      <Header title="Admin · Datos" subtitle="Sincronización y programas" right={<ProfileButton />} />
      <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }} keyboardShouldPersistTaps="handled">
        <Card>
          <Text style={s.h}>ESTADO</Text>
          <Text style={s.v}>{status ? `${status.total_results.toLocaleString('es-CO')} marcas` : 'Cargando…'}</Text>
          {status?.latest_result_date ? <Text style={s.sub}>Datos hasta: {status.latest_result_date}</Text> : null}
          <Text style={s.sub}>Última sincronización: {last ? `${new Date(last.run_at).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })} · ${last.inserted} nuevas` : 'sin registros'}</Text>
          {run ? <Text style={s.sub}>Ejecución: {run.status}{run.conclusion ? ` · ${run.conclusion}` : ''}</Text> : null}
        </Card>

        <Card>
          <Text style={s.h}>SINCRONIZAR RANKING FECNA</Text>
          <Text style={[s.sub, { marginBottom: 12 }]}>
            Trae solo las novedades desde la última marca guardada, con un margen de 30 días por si FECNA publica resultados con retraso.
          </Text>
          <View style={{ gap: 12 }}>
            <Button title="Sincronizar ahora" onPress={() => setConfirmSync('incremental')} loading={busy} />
            <Button title="Sincronización completa" variant="outline" onPress={() => setConfirmSync('completa')} disabled={busy} />
          </View>
        </Card>

        <Card>
          <Text style={s.h}>PROGRAMA DE CAMPEONATO (PDF)</Text>
          <View style={{ gap: 12, marginTop: 8 }}>
            <Button title={pdf ? pdf.name : 'Elegir PDF'} variant="outline" onPress={choose} />
            <Button title="Publicar programa" onPress={() => setConfirmPub(true)} disabled={!pdf} loading={busy} />
          </View>
        </Card>

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
});
