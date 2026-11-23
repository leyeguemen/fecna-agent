import Constants from 'expo-constants';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useState } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { api, Item } from '../../api';
import { useAuth } from '../../auth';
import { c, font } from '../../theme';
import { Avatar, Button, Card, Chip, ConfirmDialog, ErrorText, Field, Icon } from '../../ui';

export default function Perfil() {
  const { user, signOut, can, changePassword } = useAuth();
  const [me, setMe] = useState<Item | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [logout, setLogout] = useState(false);
  const [del, setDel] = useState(false);
  const [delText, setDelText] = useState('');
  const [pwd, setPwd] = useState(false);
  const [cur, setCur] = useState('');
  const [next, setNext] = useState('');
  const [rep, setRep] = useState(false);
  const [repTitle, setRepTitle] = useState('');
  const [repText, setRepText] = useState('');
  const [repScreen, setRepScreen] = useState('');
  const [repBusy, setRepBusy] = useState(false);

  const load = useCallback(() => {
    api('/me').then(setMe).catch((e) => setError(e.message));
  }, []);
  useFocusEffect(load);

  if (!user) return null;

  const unlink = async () => { await api('/me/swimmer', { method: 'DELETE' }).catch((e) => setError(e.message)); load(); };
  const changePwd = async () => {
    setError(null);
    try {
      await changePassword(cur, next);
      setPwd(false); setCur(''); setNext(''); setNotice('Contraseña actualizada. Se cerró la sesión en tus otros dispositivos.');
    } catch (e: any) { setError(e.message); }
  };
  const sendReport = async () => {
    setRepBusy(true); setError(null);
    try {
      await api('/reports', { body: { title: repTitle.trim(), description: repText.trim(), screen: repScreen.trim() || undefined,
        platform: Platform.OS, app_version: Constants.expoConfig?.version } });
      setRep(false); setRepTitle(''); setRepText(''); setRepScreen('');
      setNotice('Reporte enviado. Aparecerá en el tablero de GitHub en unos segundos. ¡Gracias!');
    } catch (e: any) { setError(e.message); }
    finally { setRepBusy(false); }
  };
  const removeAccount = async () => {
    try { await api('/me', { method: 'DELETE' }); setDel(false); signOut(); }
    catch (e: any) { setDel(false); setError(e.message); }
  };

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Avatar label={user.email} size={60} />
        <View style={{ flex: 1 }}>
          <Text style={s.email} numberOfLines={1}>{user.email}</Text>
          <Text style={s.role}>{user.role === 'admin' ? 'Administrador' : 'Usuario'}</Text>
        </View>
      </View>
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
        <Text style={s.h}>MI NADADOR</Text>
        {me?.swimmer ? (
          <Card>
            <Pressable style={s.row} onPress={() => router.push({ pathname: '/nadador', params: { id: me.swimmer.swimmer_id } })}>
              <Avatar label={me.swimmer.swimmer_name} size={44} />
              <View style={{ flex: 1 }}>
                <Text style={s.name}>{me.swimmer.swimmer_name}</Text>
                <Text style={s.sub}>Verificado · {me.swimmer.club ?? '—'}</Text>
              </View>
              <Icon name="chevron" size={20} />
            </Pressable>
            <Pressable onPress={unlink}><Text style={[s.link, { marginTop: 10 }]}>Desvincular</Text></Pressable>
          </Card>
        ) : (
          <Button title="Vincular mi nadador" variant="outline" onPress={() => router.push('/vincular')} />
        )}

        <Text style={s.h}>NADADORES QUE SIGO</Text>
        <View style={s.chips}>
          {(me?.following ?? []).map((f: Item) => (
            <Chip key={f.swimmer_id} label={f.swimmer_name} onPress={() => router.push({ pathname: '/nadador', params: { id: f.swimmer_id } })} />
          ))}
          {me && me.following.length === 0 ? <Text style={s.sub}>Aún no sigues a nadie. Usa “Seguir” en la ficha de un nadador.</Text> : null}
        </View>

        <Text style={s.h}>CUENTA</Text>
        <Card>
          <Pressable style={s.line} onPress={() => { setError(null); setPwd(true); }}><Text style={s.text}>Cambiar contraseña</Text><Icon name="chevron" size={18} /></Pressable>
          {can('reportar_problema') ? (
            <Pressable style={s.line} onPress={() => { setError(null); setRep(true); }}><Text style={s.text}>Reportar un problema</Text><Icon name="chevron" size={18} /></Pressable>
          ) : null}
          <Pressable style={s.line} onPress={() => router.push('/terminos')}><Text style={s.text}>Términos y condiciones</Text><Icon name="chevron" size={18} /></Pressable>
          <Pressable style={[s.line, { borderBottomWidth: 0 }]} onPress={() => { setDelText(''); setDel(true); }}><Text style={s.text}>Eliminar mi cuenta y datos</Text><Icon name="chevron" size={18} /></Pressable>
        </Card>

        {notice ? <Text style={{ color: c.deep, fontFamily: font.semi }}>{notice}</Text> : null}
        <ErrorText text={error} />
        {/* El cierre de sesión vive solo aquí (decisión de diseño). */}
        <Button title="Cerrar sesión" variant="outline" onPress={() => setLogout(true)} />
      </ScrollView>

      <ConfirmDialog visible={logout} title="¿Cerrar sesión?" confirmLabel="Cerrar sesión"
        message="Tendrás que ingresar de nuevo con tu correo y contraseña."
        onConfirm={() => { setLogout(false); signOut(); }} onCancel={() => setLogout(false)} />

      <ConfirmDialog visible={rep} title="Reportar un problema" confirmLabel={repBusy ? 'Enviando…' : 'Enviar'}
        message="Tu reporte se publica en GitHub y lo puede ver cualquiera. No incluyas contraseñas, nombres de nadadores, fechas de nacimiento ni otros datos personales."
        confirmDisabled={repBusy || repTitle.trim().length < 3 || repText.trim().length < 5} onConfirm={sendReport} onCancel={() => setRep(false)}>
        <View style={{ gap: 10, marginTop: 10 }}>
          <Field label="Título" value={repTitle} onChangeText={setRepTitle} maxLength={120} placeholder="Qué falla, en pocas palabras" />
          <Field label="¿Qué pasó?" value={repText} onChangeText={setRepText} maxLength={2000} multiline numberOfLines={4}
            placeholder="Cuéntalo con tus palabras" style={{ height: 110, textAlignVertical: 'top', paddingTop: 12 }} />
          <Field label="Pantalla (opcional)" value={repScreen} onChangeText={setRepScreen} maxLength={40} placeholder="Torneos, Ranking…" />
          <ErrorText text={error} />
        </View>
      </ConfirmDialog>

      <ConfirmDialog visible={pwd} title="Cambiar contraseña" confirmLabel="Guardar" message="Mínimo 8 caracteres, con letras y números."
        confirmDisabled={!cur || next.length < 8} onConfirm={changePwd} onCancel={() => setPwd(false)}>
        <View style={{ gap: 10, marginTop: 10 }}>
          <Field label="Contraseña actual" value={cur} onChangeText={setCur} secureTextEntry />
          <Field label="Contraseña nueva" value={next} onChangeText={setNext} secureTextEntry />
          <ErrorText text={error} />
        </View>
      </ConfirmDialog>

      <ConfirmDialog visible={del} danger title="¿Eliminar tu cuenta?" confirmLabel="Eliminar"
        message="Se borran tu perfil, el vínculo con tu nadador y los nadadores que sigues. Esta acción no se puede deshacer."
        confirmDisabled={delText !== 'ELIMINAR'} onConfirm={removeAccount} onCancel={() => setDel(false)}>
        <Text style={[s.sub, { marginTop: 12 }]}>Escribe ELIMINAR para confirmar</Text>
        <TextInput value={delText} onChangeText={setDelText} autoCapitalize="characters" placeholder="ELIMINAR" placeholderTextColor="#8AA3B5" style={s.confirm} />
      </ConfirmDialog>
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  header: { backgroundColor: c.deep, padding: 20, paddingTop: 56, flexDirection: 'row', alignItems: 'center', gap: 14 },
  email: { color: c.white, fontFamily: font.title, fontSize: 17 },
  role: { color: c.headerSub, fontFamily: font.body, fontSize: 12, marginTop: 2 },
  h: { fontFamily: font.bold, fontSize: 11, letterSpacing: 0.6, color: c.muted, marginTop: 4 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  name: { fontFamily: font.semi, color: c.text, fontSize: 14 },
  sub: { fontFamily: font.body, color: c.muted, fontSize: 12 },
  link: { color: c.primary, fontFamily: font.semi, fontSize: 13 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  line: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: c.border },
  text: { fontFamily: font.body, fontSize: 14, color: c.text },
  confirm: { height: 44, marginTop: 4, borderWidth: 1, borderColor: c.input, borderRadius: 10, paddingHorizontal: 12, fontSize: 14, fontFamily: font.body },
});
