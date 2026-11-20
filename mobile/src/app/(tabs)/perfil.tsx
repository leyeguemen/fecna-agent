import { router } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../../auth';
import { c, font } from '../../theme';
import { Avatar, Button, ConfirmDialog, Icon } from '../../ui';

export default function Perfil() {
  const { user, signOut } = useAuth();
  const [confirm, setConfirm] = useState(false);
  if (!user) return null;

  return (
    <View style={s.root}>
      <View style={s.header}>
        <Avatar label={user.email} size={60} />
        <View style={{ flex: 1 }}>
          <Text style={s.email} numberOfLines={1}>{user.email}</Text>
          <Text style={s.role}>{user.role === 'admin' ? 'Administrador' : 'Usuario'}</Text>
        </View>
      </View>
      <View style={{ padding: 16, gap: 12 }}>
        <Button title="Volver" variant="outline" onPress={() => router.back()} />
        {/* El cierre de sesión vive solo aquí (decisión de diseño). */}
        <Button title="Cerrar sesión" variant="outline" onPress={() => setConfirm(true)} />
      </View>
      <ConfirmDialog visible={confirm} title="¿Cerrar sesión?" confirmLabel="Cerrar sesión"
        message="Tendrás que ingresar de nuevo con tu correo y contraseña."
        onConfirm={() => { setConfirm(false); signOut(); }} onCancel={() => setConfirm(false)} />
    </View>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  header: { backgroundColor: c.deep, padding: 20, paddingTop: 56, flexDirection: 'row', alignItems: 'center', gap: 14 },
  email: { color: c.white, fontFamily: font.title, fontSize: 17 },
  role: { color: c.headerSub, fontFamily: font.body, fontSize: 12, marginTop: 2 },
});
