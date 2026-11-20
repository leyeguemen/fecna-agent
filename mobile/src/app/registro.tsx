import { Link } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../auth';
import { c, font } from '../theme';
import { Button, ErrorText, Field } from '../ui';

export default function Registro() {
  const { signUp } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [again, setAgain] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const mismatch = again.length > 0 && again !== password;
  const submit = async () => {
    setBusy(true); setError(null);
    try { await signUp(email.trim(), password); }
    catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  return (
    <KeyboardAvoidingView style={s.root} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView contentContainerStyle={{ gap: 14, padding: 24, paddingTop: 72 }} keyboardShouldPersistTaps="handled">
        <Text style={s.title}>Crear cuenta</Text>
        <Text style={s.sub}>Con tu cuenta podrás consultar rankings, marcas y campeonatos.</Text>
        <Field label="Correo" value={email} onChangeText={setEmail} keyboardType="email-address" placeholder="tu@correo.com" />
        <Field label="Contraseña" value={password} onChangeText={setPassword} secureTextEntry placeholder="Mínimo 8 caracteres" />
        <Field label="Repite la contraseña" value={again} onChangeText={setAgain} secureTextEntry placeholder="••••••••" />
        <ErrorText text={mismatch ? 'Las contraseñas no coinciden.' : error} />
        <Button title="Crear cuenta" onPress={submit} loading={busy} disabled={!email || password.length < 8 || password !== again} />
        <Text style={s.small}>¿Ya tienes cuenta? <Link href="/login" style={s.link}>Ingresa</Link></Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.bg },
  title: { fontFamily: font.title, fontSize: 28, color: c.deep },
  sub: { fontFamily: font.body, fontSize: 14, color: c.muted, lineHeight: 20 },
  small: { textAlign: 'center', color: c.muted, fontFamily: font.body, fontSize: 13 },
  link: { color: c.primary, fontFamily: font.semi },
});
