/** The browser only talks to the two local services, through these rewrites.
 *  Snowflake credentials stay in the services; nothing secret reaches the UI. */
const PROVIDER_URL = process.env.PROVIDER_URL || "http://localhost:8001";
const PAYER_URL = process.env.PAYER_URL || "http://localhost:8002";

export default {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/svc/provider/:path*", destination: `${PROVIDER_URL}/:path*` },
      { source: "/svc/payer/:path*", destination: `${PAYER_URL}/:path*` },
    ];
  },
};
