import { Link } from 'expo-router';
import { SOURCE_NOTE } from '../legal';
import { useState } from 'react';
import { Image, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useAuth } from '../auth';
import { c, font } from '../theme';
import { Button, ErrorText, Field } from '../ui';

export default function Login() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true); setError(null);
    try { await signIn(email.trim(), password); }
    catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  return (
    <KeyboardAvoidingView style={s.root} behavior="padding">
      <View style={s.hero}>
        <Image source={require('../../assets/splash-icon.png')} style={s.logo} accessibilityLabel="Logo de NATIA" />
        <Text style={s.brand}>NATIA</Text>
        <Text style={s.tag}>{'Tu asistente de natación.\nConsulta tus marcas. Entiende tu progreso.'}</Text>
      </View>
      <ScrollView style={s.sheet} contentContainerStyle={{ gap: 14, padding: 24, paddingBottom: 36 }} keyboardShouldPersistTaps="handled">
        <Field label="Correo" value={email} onChangeText={setEmail} keyboardType="email-address" placeholder="tu@correo.com" />
        <Field label="Contraseña" value={password} onChangeText={setPassword} secureTextEntry placeholder="••••••••" />
        <ErrorText text={error} />
        <Button title="Ingresar" onPress={submit} loading={busy} disabled={!email || !password} />
        <Text style={s.small}>¿Sin cuenta? <Link href="/registro" style={s.link}>Regístrate</Link></Text>
        <Text style={[s.small, { fontSize: 11 }]}>{SOURCE_NOTE}</Text>
        <Text style={[s.small, { fontSize: 12 }]}><Link href="/terminos" style={s.link}>Términos y condiciones</Link></Text>
        {/* En la web, la landing es una página estática fuera de la app: se abre con una carga completa. */}
        {Platform.OS === 'web' ? (
          <Text style={[s.small, { fontSize: 12 }]}>
            <Text accessibilityRole="link" style={s.link} onPress={() => window.location.assign('/bienvenida')}>¿Qué es NATIA? Conócela</Text>
          </Text>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.deep },
  hero: { flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 32, gap: 12 },
  logo: { width: 96, height: 96, borderRadius: 26, marginBottom: 4 },
  brand: { color: c.white, fontFamily: font.title, fontSize: 30 },
  tag: { color: c.headerSub, fontFamily: font.body, fontSize: 14, textAlign: 'center', lineHeight: 20 },
  sheet: { flexGrow: 0, backgroundColor: c.white, borderTopLeftRadius: 28, borderTopRightRadius: 28 },
  small: { textAlign: 'center', color: c.muted, fontFamily: font.body, fontSize: 13 },
  link: { color: c.primary, fontFamily: font.semi },
});
