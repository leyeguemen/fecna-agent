import * as DocumentPicker from 'expo-document-picker';
import { useCallback, useEffect, useState } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { api, Item } from '../../api';
import { useAuth } from '../../auth';
import { ProfileButton } from '../../ProfileButton';
import { c, font } from '../../theme';
import { Button, Card, ConfirmDialog, ErrorText, Header } from '../../ui';

export default function Admin() {
  const { user, can } = useAuth();
  const canSync = can('sincronizar');
  const canUpload = can('cargar_programa');
  const canUsers = can('gestionar_usuarios');
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

  // --- Usuarios y roles ---
  const [users, setUsers] = useState<Item[]>([]);
  const [uq, setUq] = useState('');
  const [roles, setRoles] = useState<Item[]>([]);
  const [roleChange, setRoleChange] = useState<{ u: Item; role: 'admin' | 'user' } | null>(null);
  const [roleBusy, setRoleBusy] = useState(false);

  useEffect(() => {
    if (!canUsers) return;
    api('/admin/roles').then((r) => setRoles(r.roles)).catch(() => {});
  }, [canUsers]);

  useEffect(() => {
    if (!canUsers) return;
    const t = setTimeout(() => {
      api(`/admin/users?q=${encodeURIComponent(uq.trim())}`).then((r) => setUsers(r.items)).catch((e) => setError(e.message));
    }, 300);
    return () => clearTimeout(t);
  }, [canUsers, uq]);

  const applyRole = async () => {
    if (!roleChange) return;
    const { u, role } = roleChange;
    setRoleBusy(true); setError(null); setMsg(null);
    try {
      await api(`/admin/users/${u.id}/role`, { method: 'PUT', body: { role } });
      setUsers((list) => list.map((x) => (x.id === u.id ? { ...x, role, role_name: role === 'admin' ? 'Administrador' : 'Usuario' } : x)));
      setMsg(`${u.email} ahora es ${role === 'admin' ? 'administrador' : 'usuario'}. El cambio aplica de inmediato.`);
    } catch (e: any) { setError(e.message); }
    finally { setRoleBusy(false); setRoleChange(null); }
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

        {canUpload ? <Card>
          <Text style={s.h}>PROGRAMA DE CAMPEONATO (PDF)</Text>
          <View style={{ gap: 12, marginTop: 8 }}>
            <Button title={pdf ? pdf.name : 'Elegir PDF'} variant="outline" onPress={choose} disabled={busy} />
            <Button title="Publicar programa" onPress={() => setConfirmPub(true)} disabled={!pdf || busy} loading={publishing} />
            {publishing ? <Text style={s.sub}>Subiendo y leyendo el programa… puede tardar hasta un minuto. No cierres la app.</Text> : null}
          </View>
        </Card> : null}

        {canUsers ? (
          <Card>
            <Text style={s.h}>USUARIOS Y ROLES</Text>
            <TextInput value={uq} onChangeText={setUq} placeholder="Buscar por correo" placeholderTextColor="#8AA3B5" autoCapitalize="none" style={[s.search, { marginTop: 8 }]} />
            <View style={{ marginTop: 8 }}>
              {users.length === 0 ? <Text style={s.sub}>Sin usuarios para esa búsqueda.</Text> : null}
              {users.map((u) => {
                const self = u.email === user?.email;
                const toAdmin = u.role !== 'admin';
                return (
                  <View key={u.id} style={s.userRow}>
                    <View style={{ flex: 1 }}>
                      <Text style={s.userEmail} numberOfLines={1}>{u.email}{self ? ' (tú)' : ''}</Text>
                      <Text style={s.sub}>{u.role_name}</Text>
                    </View>
                    {!self ? (
                      <Pressable onPress={() => setRoleChange({ u, role: toAdmin ? 'admin' : 'user' })} accessibilityRole="button" style={s.roleBtn}>
                        <Text style={s.roleBtnText}>{toAdmin ? 'Hacer admin' : 'Quitar admin'}</Text>
                      </Pressable>
                    ) : null}
                  </View>
                );
              })}
            </View>
            {roles.length ? (
              <View style={{ marginTop: 12, gap: 6 }}>
                <Text style={s.h}>QUÉ PUEDE HACER CADA ROL</Text>
                {roles.map((r) => (
                  <Text key={r.id} style={s.sub}><Text style={{ fontFamily: font.semi, color: c.text }}>{r.name}: </Text>{r.permissions.map((p: Item) => p.label).join(' · ')}</Text>
                ))}
              </View>
            ) : null}
          </Card>
        ) : null}

        {msg ? <Text style={{ color: c.deep, fontFamily: font.semi }}>{msg}</Text> : null}
        <ErrorText text={error} />
      </ScrollView>

      <ConfirmDialog visible={confirmSync === 'incremental'} title="¿Sincronizar el ranking?" confirmLabel="Sincronizar"
        message="Se consultarán las novedades de FECNA desde la última actualización. Puede tardar varios minutos y se ejecuta en segundo plano; puedes cerrar la app."
        onConfirm={sync} onCancel={() => setConfirmSync(null)} />
      <ConfirmDialog visible={confirmSync === 'completa'} title="¿Sincronización completa?" confirmLabel="Sincronizar"
        message="Se vuelve a consultar todo el ranking de FECNA desde 2024. Es lenta (puede tardar más de una hora) y sirve para reparar huecos. Para el uso normal basta «Sincronizar ahora»."
        onConfirm={sync} onCancel={() => setConfirmSync(null)} />
      <ConfirmDialog visible={!!roleChange} title={roleChange?.role === 'admin' ? '¿Dar rol de administrador?' : '¿Quitar el rol de administrador?'}
        confirmLabel={roleBusy ? 'Guardando…' : 'Confirmar'} confirmDisabled={roleBusy} danger={roleChange?.role !== 'admin'}
        message={roleChange?.role === 'admin'
          ? `${roleChange?.u.email} podrá sincronizar el ranking, cargar y eliminar programas y cambiar roles.`
          : `${roleChange?.u.email} dejará de poder administrar la app. Pasará a ser usuario normal.`}
        onConfirm={applyRole} onCancel={() => setRoleChange(null)} />
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
  userRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 10, borderTopWidth: 1, borderTopColor: c.border },
  userEmail: { fontFamily: font.semi, fontSize: 14, color: c.text },
  roleBtn: { borderWidth: 1, borderColor: c.primary, borderRadius: 10, paddingVertical: 6, paddingHorizontal: 10 },
  roleBtnText: { color: c.primary, fontFamily: font.semi, fontSize: 12 },
});
