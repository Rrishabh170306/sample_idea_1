import NextAuth from 'next-auth';
import Google from 'next-auth/providers/google';

const protectedRoutes = ['/profile'];

export const { handlers, auth, signIn, signOut } = NextAuth({
  trustHost: true,
  secret: process.env.AUTH_SECRET,
  pages: {
    signIn: '/auth',
  },
  session: {
    strategy: 'jwt',
  },
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID ?? '',
      clientSecret: process.env.AUTH_GOOGLE_SECRET ?? '',
    }),
  ],
  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      const isProtectedRoute = protectedRoutes.some((route) => nextUrl.pathname.startsWith(route));

      if (!isProtectedRoute) {
        return true;
      }

      return !!auth;
    },
  },
});
