import { router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { api, Item } from '../../api';
import { useAuth } from '../../auth';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Button, Card, ConfirmDialog, ErrorText, Header } from '../../ui';

export default function Sincronizar() {
  const { can } = useAuth();
  const canSync = can('sincronizar');
  const [status, setStatus] = useState<Item | null>(null);
  const [confirmSync, setConfirmSync] = useState<null | 'incremental' | 'completa'>(null);
  const [syncing, setSyncing] = useState(false);
  const busy = syncing;
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

  const run = status?.run;
  const last = status?.last_sync;

  return (
    <View style={s.root}>
      <Header title="Sincronizar ranking" subtitle="Datos de FECNA" onBack={() => router.replace('/config')} right={<ProfileButton />} />
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

        {msg ? <Text style={{ color: c.deep, fontFamily: font.semi }}>{msg}</Text> : null}
        <ErrorText text={error} />
      </ScrollView>

      <ConfirmDialog visible={confirmSync === 'incremental'} title="¿Sincronizar el ranking?" confirmLabel="Sincronizar"
        message="Se consultarán las novedades de FECNA desde la última actualización. Puede tardar varios minutos y se ejecuta en segundo plano; puedes cerrar la app."
        onConfirm={sync} onCancel={() => setConfirmSync(null)} />
      <ConfirmDialog visible={confirmSync === 'completa'} title="¿Sincronización completa?" confirmLabel="Sincronizar"
        message="Se vuelve a consultar todo el ranking de FECNA desde 2024. Es lenta (puede tardar más de una hora) y sirve para reparar huecos. Para el uso normal basta «Sincronizar ahora»."
        onConfirm={sync} onCancel={() => setConfirmSync(null)} />
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  h: { fontFamily: font.bold, fontSize: 11, letterSpacing: 0.6, color: c.muted },
  v: { fontFamily: font.title, fontSize: 24, color: c.deep, marginTop: 4 },
  sub: { fontFamily: font.body, fontSize: 12, color: c.muted, marginTop: 4 },
});
