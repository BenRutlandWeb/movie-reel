import { filterProviders } from '../utils/streamerPrefs'

const STREAM_TYPES = new Set(['flatrate', 'free', 'ads'])

const TYPE_LABELS = {
  flatrate: 'subscription',
  free: 'free',
  ads: 'free with ads',
  rent: 'rent',
  buy: 'buy',
}

export default function StreamingProviders({ providers }) {
  const visible = filterProviders(providers)
  const stream = visible.filter((p) => STREAM_TYPES.has(p.provider_type))
  const transactional = visible.filter((p) => !STREAM_TYPES.has(p.provider_type))

  if (!visible.length) {
    return null
  }

  return (
    <div>
      {stream.length > 0 && (
        <div className="section">
          <h2>Stream</h2>
          <div className="providers">
            {stream.map((p) => (
              <Provider key={`${p.provider_id}-${p.provider_type}`} provider={p} />
            ))}
          </div>
        </div>
      )}
      {transactional.length > 0 && (
        <div className="section">
          <h2>Rent or Buy</h2>
          <div className="providers">
            {transactional.map((p) => (
              <Provider key={`${p.provider_id}-${p.provider_type}`} provider={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function Provider({ provider }) {
  return (
    <div className="provider">
      {provider.logo_url ? (
        <img src={provider.logo_url} alt={provider.provider_name} />
      ) : (
        <span>📺</span>
      )}
      <div>
        <div>{provider.provider_name}</div>
        <div className="provider-type">{TYPE_LABELS[provider.provider_type] || provider.provider_type}</div>
      </div>
    </div>
  )
}
