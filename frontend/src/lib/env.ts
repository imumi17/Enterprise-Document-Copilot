const requiredEnvVars = [
  "VITE_API_BASE_URL",
  "VITE_SUPABASE_URL",
  "VITE_SUPABASE_ANON_KEY",
] as const;

type EnvVar = (typeof requiredEnvVars)[number];

function readEnv(name: EnvVar): string {
  const value = import.meta.env[name];
  if (!value || value.trim() === "") {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value.trim();
}

export const env = {
  apiBaseUrl: readEnv("VITE_API_BASE_URL").replace(/\/$/, ""),
  supabaseUrl: readEnv("VITE_SUPABASE_URL"),
  supabaseAnonKey: readEnv("VITE_SUPABASE_ANON_KEY"),
};
