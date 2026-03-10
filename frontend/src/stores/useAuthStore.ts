import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { supabase } from '@/lib/supabase';
import { api } from '@/lib/api';
import type { User, ConsentPayload } from '@/types';

interface AuthStore {
  user: User | null;
  token: string | null;
  loading: boolean;
  consentGiven: boolean;

  /* Actions */
  initialize: () => Promise<void>;
  signUp: (email: string, password: string, displayName?: string) => Promise<void>;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  recordConsent: (consent: ConsentPayload) => Promise<void>;
  setUser: (user: User | null) => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, _get) => ({
      user: null,
      token: null,
      loading: true,
      consentGiven: false,

      initialize: async () => {
        try {
          const { data } = await supabase.auth.getSession();
          if (data.session) {
            const token = data.session.access_token;
            set({ token });

            // Store token for api.ts to pick up
            localStorage.setItem(
              'sb-auth-token',
              JSON.stringify({ access_token: token }),
            );

            const user = await api.getMe();
            set({ user, loading: false });
          } else {
            set({ user: null, token: null, loading: false });
          }
        } catch {
          set({ user: null, token: null, loading: false });
        }

        // Listen for auth state changes
        supabase.auth.onAuthStateChange((_event, session) => {
          if (session) {
            const token = session.access_token;
            set({ token });
            localStorage.setItem(
              'sb-auth-token',
              JSON.stringify({ access_token: token }),
            );
          } else {
            set({ user: null, token: null, consentGiven: false });
            localStorage.removeItem('sb-auth-token');
          }
        });
      },

      signUp: async (email, password, displayName) => {
        set({ loading: true });
        try {
          const { data, error } = await supabase.auth.signUp({
            email,
            password,
            options: { data: { display_name: displayName } },
          });
          if (error) throw error;

          const token = data.session?.access_token ?? null;
          if (token) {
            localStorage.setItem(
              'sb-auth-token',
              JSON.stringify({ access_token: token }),
            );
          }

          set({
            user: data.user
              ? {
                  id: data.user.id,
                  email: data.user.email!,
                  display_name: displayName,
                  created_at: data.user.created_at,
                }
              : null,
            token,
            loading: false,
          });
        } catch (err) {
          set({ loading: false });
          throw err;
        }
      },

      signIn: async (email, password) => {
        set({ loading: true });
        try {
          const { data, error } = await supabase.auth.signInWithPassword({
            email,
            password,
          });
          if (error) throw error;

          const token = data.session?.access_token ?? null;
          if (token) {
            localStorage.setItem(
              'sb-auth-token',
              JSON.stringify({ access_token: token }),
            );
          }

          set({
            user: data.user
              ? {
                  id: data.user.id,
                  email: data.user.email!,
                  display_name: data.user.user_metadata?.display_name,
                  created_at: data.user.created_at,
                }
              : null,
            token,
            loading: false,
          });
        } catch (err) {
          set({ loading: false });
          throw err;
        }
      },

      signOut: async () => {
        await supabase.auth.signOut();
        localStorage.removeItem('sb-auth-token');
        set({ user: null, token: null, consentGiven: false });
      },

      recordConsent: async (consent) => {
        await api.recordConsent(consent);
        set({ consentGiven: true });
      },

      setUser: (user) => set({ user }),
    }),
    {
      name: 'tdl-auth',
      partialize: (state) => ({
        consentGiven: state.consentGiven,
      }),
    },
  ),
);
