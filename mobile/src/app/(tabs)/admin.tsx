import * as DocumentPicker from 'expo-document-picker';
import { useCallback, useEffect, useState } from 'react';
import { Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { api, Item } from '../../api';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Button, Card, ConfirmDialog, ErrorText, Field, Header } from '../../ui';

const daysAgo = (n: number) => new Date(Date.now() - n * 864e5).toISOString().slice(0, 10);

export default function Admin() {
  const [status, setStatus] = useState<Item | null>(null);
  const [inicio, setInicio] = useState(daysAgo(45));
  const [confirmSync, setConfirmSync] = useState(false);
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
    setConfirmSync(false); setBusy(true); setError(null); setMsg(null);
    try {
      await api('/admin/sync', { body: { inicio } });
      setMsg('Sincronización en cola. Corre en segundo plano; puedes cerrar la app.');
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
          <Text style={s.sub}>Última sincronización: {last ? `${new Date(last.run_at).toLocaleString('es-CO', { dateStyle: 'medium', timeStyle: 'short' })} · ${last.inserted} nuevas` : 'sin registros'}</Text>
          {run ? <Text style={s.sub}>Ejecución: {run.status}{run.conclusion ? ` · ${run.conclusion}` : ''}</Text> : null}
        </Card>

        <Card>
          <Text style={s.h}>SINCRONIZAR RANKING FECNA</Text>
          <View style={{ gap: 12, marginTop: 8 }}>
            <Field label="Desde (AAAA-MM-DD)" value={inicio} onChangeText={setInicio} placeholder="2026-01-01" />
            <Button title="Sincronizar ahora" onPress={() => setConfirmSync(true)} loading={busy} disabled={!/^\d{4}-\d{2}-\d{2}$/.test(inicio)} />
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

      <ConfirmDialog visible={confirmSync} title="¿Sincronizar el ranking?" confirmLabel="Sincronizar"
        message={`Se consultará el sitio de FECNA desde ${inicio}. Puede tardar varios minutos y se ejecuta en segundo plano; puedes cerrar la app.`}
        onConfirm={sync} onCancel={() => setConfirmSync(false)} />
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
