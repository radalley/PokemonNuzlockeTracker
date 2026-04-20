import SiteHeader from '../components/SiteHeader'

const GUIDE_LINKS = [
  {
    name: 'Serebii',
    url: 'https://www.serebii.net/',
    description: 'A Pokemon data hub with game walkthroughs, encounter details, move data, item data, and event coverage.',
  },
  {
    name: 'Bulbapedia',
    url: 'https://bulbapedia.bulbagarden.net/',
    description: 'Another Pokemon data hub with broad wiki-style coverage for species, mechanics, locations, trainers, and game-specific details.',
  },
  {
    name: 'PokemonDB',
    url: 'https://pokemondb.net/',
    description: 'A comprehensive Pokemon database with information on moves, abilities, locations, and more.',
  }
]

function Guides() {
  return (
    <div className="guides-page">
      <SiteHeader showHomeButton />
      <div className="guides-panel">
        <h1>Guides</h1>
        <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '16px' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '10px 12px', borderBottom: '1px solid #343a47', fontSize: '0.82rem', color: '#9aa3b5' }}>Website</th>
              <th style={{ textAlign: 'left', padding: '10px 12px', borderBottom: '1px solid #343a47', fontSize: '0.82rem', color: '#9aa3b5' }}>Description</th>
            </tr>
          </thead>
          <tbody>
            {GUIDE_LINKS.map(site => (
              <tr key={site.url}>
                <td style={{ padding: '12px', borderBottom: '1px solid #262c38', verticalAlign: 'top', whiteSpace: 'nowrap' }}>
                  <a
                    href={site.url}
                    target="_blank"
                    rel="noreferrer"
                    style={{ color: '#7ec8e3', textDecoration: 'none', fontWeight: 'bold' }}
                  >
                    {site.name}
                  </a>
                </td>
                <td style={{ padding: '12px', borderBottom: '1px solid #262c38', color: '#d6dbe6', lineHeight: 1.45 }}>
                  {site.description}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Guides