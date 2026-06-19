import { Html, Head, Main, NextScript } from "next/document";

export default function Document() {
  return (
    <Html lang="en">
      <Head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico?v=3" sizes="any" />
        <link rel="icon" type="image/svg+xml" href="/logo.svg?v=3" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png?v=3" />
        <link rel="manifest" href="/manifest.json?v=3" />
        <meta name="theme-color" content="#000000" />
      </Head>
      <body className="antialiased">
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
