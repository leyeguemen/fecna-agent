import { router, useLocalSearchParams } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import { KeyboardAvoidingView, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import type { AuthResp } from '../api';
import { useAuth } from '../auth';
import { c, font } from '../theme';
import { Button, ErrorText, Field, Icon } from '../ui';

const RESEND_SECONDS = 60; // igual que RESET_RESEND en la API
const DIGITS = 6;

/** «ana.perez@gmail.com» → «an•••@gmail.com» */
const maskEmail = (email: string) => {
  const [name, domain] = email.split('@');
  return domain ? `${name.slice(0, 2)}•••@${domain}` : email;
};

const TEXTS = {
  1: ['¿Olvidaste tu contraseña?', 'Escribe el correo con el que te registraste y te enviamos un código para crear una nueva.'],
  2: ['Revisa tu correo', ''],
  3: ['Contraseña actualizada', 'Ya puedes entrar con tu nueva contraseña.'],
} as const;

export default function Recuperar() {
  const { forgotPassword, resetPassword, startSession } = useAuth();
  const params = useLocalSearchParams<{ email?: string }>();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [email, setEmail] = useState(params.email ?? '');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [again, setAgain] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [wait, setWait] = useState(0); // segundos para poder reenviar
  const [session, setSession] = useState<AuthResp | null>(null);
  const codeRef = useRef<React.ComponentRef<typeof TextInput>>(null);

  useEffect(() => {
    if (wait <= 0) return;
    const t = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(t);
  }, [wait]);

  const send = async () => {
    setBusy(true); setError(null);
    try {
      await forgotPassword(email.trim());
      setStep(2); setWait(RESEND_SECONDS); setCode('');
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  const reset = async () => {
    setBusy(true); setError(null);
    try {
      setSession(await resetPassword(email.trim(), code, password));
      setStep(3);
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  const back = () => {
    if (step === 2) { setStep(1); setError(null); return; }
    if (router.canGoBack()) router.back(); else router.replace('/login');
  };

  const mismatch = again.length > 0 && again !== password;
  const [title, sub] = TEXTS[step];
  const subtitle = step === 2 ? `Enviamos un código a ${maskEmail(email.trim())}. Vence en 15 minutos.` : sub;
  const mm = Math.floor(wait / 60), ss = String(wait % 60).padStart(2, '0');

  return (
    <KeyboardAvoidingView style={s.root} behavior="padding">
      <View style={s.top}>
        {step !== 3 ? (
          <Pressable onPress={back} accessibilityRole="button" accessibilityLabel="Volver" hitSlop={8} style={s.backBtn}>
            <Icon name="back" color={c.white} size={20} />
          </Pressable>
        ) : null}
        <Text style={s.stepText}>Paso {step} de 3</Text>
      </View>

      <View style={s.hero}>
        <View style={s.badge}>
          <Icon name={step === 1 ? 'lock' : step === 2 ? 'mail' : 'check'} color={c.white} size={30} />
        </View>
        <Text style={s.title}>{title}</Text>
        <Text style={s.sub}>{subtitle}</Text>
        <View style={{ flexDirection: 'row', gap: 6, marginTop: 6 }}>
          {[1, 2, 3].map((n) => <View key={n} style={[s.dot, n <= step && { backgroundColor: c.accent }]} />)}
        </View>
      </View>

      <ScrollView style={s.sheet} contentContainerStyle={{ gap: 14, padding: 24, paddingBottom: 36 }} keyboardShouldPersistTaps="handled">
        {step === 1 ? (
          <>
            <Field label="Correo de tu cuenta" value={email} onChangeText={setEmail} keyboardType="email-address" placeholder="tu@correo.com" autoComplete="email" />
            <ErrorText text={error} />
            <Button title="Enviar código" onPress={send} loading={busy} disabled={!email.includes('@')} />
            <Text style={s.small}>Si el correo tiene una cuenta en NATIA, te llega un código de 6 dígitos. Revisa también la carpeta de spam.</Text>
          </>
        ) : null}

        {step === 2 ? (
          <>
            <View>
              <Text style={s.label}>Código</Text>
              {/* Un solo campo invisible sobre las 6 casillas: pegar el código del correo funciona. */}
              <Pressable onPress={() => codeRef.current?.focus()} style={s.boxes}>
                {Array.from({ length: DIGITS }, (_, i) => (
                  <View key={i} style={[s.box, i === Math.min(code.length, DIGITS - 1) && { borderColor: c.primary, borderWidth: 1.5 }]}>
                    <Text style={s.digit}>{code[i] ?? ''}</Text>
                  </View>
                ))}
                <TextInput
                  ref={codeRef}
                  value={code}
                  onChangeText={(t) => setCode(t.replace(/\D/g, '').slice(0, DIGITS))}
                  keyboardType="number-pad"
                  textContentType="oneTimeCode"
                  autoComplete="one-time-code"
                  maxLength={DIGITS}
                  autoFocus
                  accessibilityLabel="Código de 6 dígitos"
                  style={s.hiddenInput}
                  caretHidden
                />
              </Pressable>
            </View>
            <Field label="Nueva contraseña" value={password} onChangeText={setPassword} secureTextEntry placeholder="Mínimo 8 caracteres" autoComplete="new-password" />
            <Field label="Repite la contraseña" value={again} onChangeText={setAgain} secureTextEntry placeholder="••••••••" autoComplete="new-password" />
            <Text style={[s.small, { textAlign: 'left', marginTop: -6 }]}>Mínimo 8 caracteres, con letras y números.</Text>
            <ErrorText text={mismatch ? 'Las contraseñas no coinciden.' : error} />
            <Button title="Cambiar contraseña" onPress={reset} loading={busy}
              disabled={code.length !== DIGITS || password.length < 8 || password !== again} />
            {wait > 0 ? (
              <Text style={s.small}>¿No te llegó? <Text style={{ color: '#8AA3B5', fontFamily: font.semi }}>Reenviar en {mm}:{ss}</Text></Text>
            ) : (
              <Text style={s.small}>¿No te llegó? <Text style={s.link} onPress={busy ? undefined : send}>Reenviar código</Text></Text>
            )}
          </>
        ) : null}

        {step === 3 ? (
          <>
            <View style={s.notice}>
              <Icon name="shield" color="#1B8A4B" size={20} />
              <Text style={s.noticeText}>Por seguridad cerramos las sesiones abiertas en otros dispositivos.</Text>
            </View>
            <Button title="Entrar a NATIA" onPress={() => { if (session) startSession(session); }} />
          </>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: c.deep },
  top: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingTop: 52, paddingHorizontal: 20, minHeight: 92 },
  backBtn: { width: 40, height: 40, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.12)', alignItems: 'center', justifyContent: 'center' },
  stepText: { color: c.headerSub, fontFamily: font.body, fontSize: 13 },
  hero: { flex: 1, justifyContent: 'flex-end', paddingHorizontal: 28, paddingBottom: 28, gap: 10 },
  badge: { width: 64, height: 64, borderRadius: 20, backgroundColor: c.primary, alignItems: 'center', justifyContent: 'center' },
  title: { color: c.white, fontFamily: font.title, fontSize: 26, lineHeight: 30 },
  sub: { color: c.headerSub, fontFamily: font.body, fontSize: 14, lineHeight: 20 },
  dot: { height: 4, width: 28, borderRadius: 2, backgroundColor: 'rgba(255,255,255,0.25)' },
  sheet: { flexGrow: 0, backgroundColor: c.white, borderTopLeftRadius: 28, borderTopRightRadius: 28 },
  label: { fontSize: 12, color: c.muted, fontFamily: font.medium, marginBottom: 6 },
  boxes: { flexDirection: 'row', gap: 8 },
  box: { flex: 1, height: 52, borderWidth: 1, borderColor: c.input, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  digit: { fontFamily: font.title, fontSize: 22, color: c.deep },
  hiddenInput: { position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, opacity: 0.011, color: 'transparent', fontSize: 1 },
  small: { textAlign: 'center', color: c.muted, fontFamily: font.body, fontSize: 13, lineHeight: 18 },
  link: { color: c.primary, fontFamily: font.semi },
  notice: { flexDirection: 'row', gap: 10, alignItems: 'flex-start', backgroundColor: '#E8F6EE', borderRadius: 14, padding: 14 },
  noticeText: { flex: 1, fontSize: 13, color: '#14502E', fontFamily: font.body, lineHeight: 19 },
});
