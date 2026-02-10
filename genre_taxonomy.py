from typing import Dict, List, Set, Optional

class GenreTaxonomy:
    def __init__(self):
        self.taxonomy = self._build_taxonomy()
        self.subgenre_to_parent = self._build_reverse_mapping()
        
    def _build_taxonomy(self) -> Dict[str, List[str]]:
        return {
            'House': [
                'deep house',
                'tech house',
                'progressive house',
                'electro house',
                'future house',
                'tropical house',
                'bass house',
                'disco house',
                'funky house',
                'soulful house',
                'acid house',
                'afro house',
                'melodic house',
                'minimal house',
                'microhouse',
                'chicago house',
                'detroit house',
                'uk house',
                'garage house',
                'jackin house',
                'filter house',
                'french house',
                'latin house',
                'piano house',
                'vocal house'
            ],
            'Techno': [
                'minimal techno',
                'detroit techno',
                'acid techno',
                'hard techno',
                'industrial techno',
                'melodic techno',
                'progressive techno',
                'dub techno',
                'tech trance',
                'peak time techno',
                'hypnotic techno',
                'raw techno',
                'berlin techno',
                'schranz',
                'ambient techno'
            ],
            'Trance': [
                'progressive trance',
                'uplifting trance',
                'psytrance',
                'goa trance',
                'vocal trance',
                'tech trance',
                'hard trance',
                'acid trance',
                'balearic trance',
                'euphoric trance',
                'dream trance',
                'nitzhonot',
                'suomisaundi',
                'psychill',
                'dark psytrance',
                'forest psytrance',
                'full-on psytrance',
                'progressive psytrance'
            ],
            'Dubstep': [
                'brostep',
                'riddim',
                'deep dubstep',
                'melodic dubstep',
                'drumstep',
                'chillstep',
                'deathstep',
                'future dubstep',
                'tearout',
                'hybrid trap',
                'dubstep trap',
                'uk dubstep'
            ],
            'Drum and Bass': [
                'liquid drum and bass',
                'neurofunk',
                'jump up',
                'jungle',
                'darkstep',
                'techstep',
                'drumfunk',
                'intelligent drum and bass',
                'atmospheric drum and bass',
                'minimal drum and bass',
                'dancefloor drum and bass',
                'halftime drum and bass',
                'crossbreed',
                'ragga jungle',
                'breakcore',
                'dnb',
                'liquid dnb',
                'neuro dnb'
            ],
            'Trap': [
                'trap music',
                'hybrid trap',
                'festival trap',
                'future trap',
                'trapstep',
                'hard trap',
                'melodic trap',
                'wave',
                'rage',
                'plugg',
                'latin trap'
            ],
            'Bass Music': [
                'future bass',
                'melodic bass',
                'colour bass',
                'dubstep',
                'halftime',
                'breaks',
                'breakbeat',
                'uk bass',
                'bass house',
                'garage',
                'uk garage',
                'bassline',
                'grime',
                '140',
                'deep dubstep',
                'space bass'
            ],
            'Electronic Dance': [
                'big room',
                'electro',
                'complextro',
                'moombahton',
                'moombahcore',
                'melbourne bounce',
                'hardstyle',
                'hardcore',
                'happy hardcore',
                'uk hardcore',
                'gabber',
                'speedcore',
                'rawstyle',
                'jumpstyle',
                'hands up'
            ],
            'Downtempo': [
                'chillout',
                'ambient',
                'trip hop',
                'downtempo',
                'lo-fi',
                'chillhop',
                'lo-fi hip hop',
                'lounge',
                'nu jazz',
                'acid jazz',
                'ambient techno',
                'idm',
                'glitch',
                'folktronica',
                'psybient',
                'chillwave',
                'vaporwave',
                'future garage',
                'organic downtempo'
            ],
            'Indie Rock': [
                'indie rock',
                'indie pop',
                'garage rock',
                'post-punk',
                'post-punk revival',
                'noise rock',
                'art rock',
                'math rock',
                'shoegaze',
                'dream pop',
                'jangle pop',
                'chamber pop',
                'baroque pop',
                'indie folk',
                'folktronica',
                'lo-fi indie'
            ],
            'Alternative Rock': [
                'alternative rock',
                'grunge',
                'britpop',
                'madchester',
                'baggy',
                'college rock',
                'noise pop',
                'slowcore',
                'sadcore',
                'emo',
                'screamo',
                'midwest emo',
                'emo rap',
                'post-grunge'
            ],
            'Metal': [
                'heavy metal',
                'thrash metal',
                'death metal',
                'black metal',
                'doom metal',
                'power metal',
                'progressive metal',
                'metalcore',
                'deathcore',
                'djent',
                'nu metal',
                'industrial metal',
                'gothic metal',
                'symphonic metal',
                'folk metal',
                'viking metal',
                'melodic death metal',
                'technical death metal',
                'brutal death metal',
                'funeral doom'
            ],
            'Hip Hop': [
                'rap',
                'trap rap',
                'boom bap',
                'conscious hip hop',
                'gangsta rap',
                'southern hip hop',
                'east coast hip hop',
                'west coast hip hop',
                'midwest hip hop',
                'dirty south',
                'crunk',
                'hyphy',
                'cloud rap',
                'emo rap',
                'drill',
                'grime',
                'uk hip hop',
                'abstract hip hop',
                'jazz rap',
                'g-funk',
                'memphis rap',
                'phonk',
                'pluggnb'
            ],
            'R&B': [
                'r&b',
                'contemporary r&b',
                'neo soul',
                'alternative r&b',
                'progressive r&b',
                'quiet storm',
                'new jack swing',
                'soul',
                'funk',
                'p-funk',
                'boogie',
                'disco',
                'nu-disco',
                'future funk'
            ],
            'Reggae': [
                'reggae',
                'roots reggae',
                'dub',
                'reggae fusion',
                'lovers rock',
                'dancehall',
                'ragga',
                'reggaeton',
                'dembow',
                'moombahton',
                'tropical bass',
                'ska',
                'rocksteady',
                'two tone'
            ],
            'Latin': [
                'reggaeton',
                'latin trap',
                'bachata',
                'salsa',
                'cumbia',
                'merengue',
                'banda',
                'regional mexican',
                'corrido',
                'mariachi',
                'ranchera',
                'tejano',
                'norteno',
                'duranguense',
                'grupera',
                'latin pop',
                'latin urban',
                'urbano latino',
                'perreo',
                'dembow',
                'mambo',
                'cha-cha-cha',
                'son cubano',
                'timba',
                'bossa nova',
                'samba',
                'mpb',
                'forro',
                'sertanejo',
                'pagode',
                'axe',
                'tropicalia',
                'tango',
                'flamenco'
            ],
            'Country': [
                'country',
                'country pop',
                'contemporary country',
                'traditional country',
                'outlaw country',
                'alternative country',
                'alt-country',
                'americana',
                'country rock',
                'bluegrass',
                'honky tonk',
                'western swing',
                'country blues',
                'nashville sound',
                'bakersfield sound',
                'red dirt',
                'texas country',
                'country rap',
                'bro country'
            ],
            'Jazz': [
                'jazz',
                'bebop',
                'hard bop',
                'cool jazz',
                'modal jazz',
                'free jazz',
                'jazz fusion',
                'smooth jazz',
                'nu jazz',
                'acid jazz',
                'jazz funk',
                'latin jazz',
                'afro-cuban jazz',
                'spiritual jazz',
                'post-bop',
                'avant-garde jazz',
                'swing',
                'big band',
                'dixieland',
                'ragtime',
                'gypsy jazz',
                'jazz blues'
            ],
            'Classical': [
                'classical',
                'baroque',
                'romantic',
                'modern classical',
                'contemporary classical',
                'minimalism',
                'neoclassical',
                'chamber music',
                'opera',
                'orchestral',
                'symphonic',
                'choral',
                'piano',
                'string quartet',
                'avant-garde classical',
                'impressionist',
                'renaissance',
                'medieval',
                'early music',
                'classical crossover'
            ],
            'Folk': [
                'folk',
                'traditional folk',
                'contemporary folk',
                'indie folk',
                'folk rock',
                'folk pop',
                'acoustic folk',
                'freak folk',
                'psychedelic folk',
                'chamber folk',
                'anti-folk',
                'neofolk',
                'folk punk',
                'celtic',
                'irish folk',
                'scottish folk',
                'nordic folk',
                'appalachian folk',
                'bluegrass',
                'old-time',
                'singer-songwriter'
            ],
            'Funk': [
                'funk',
                'p-funk',
                'psychedelic funk',
                'funk rock',
                'funk metal',
                'jazz funk',
                'boogie',
                'go-go',
                'afrobeat',
                'afrofunk',
                'electro-funk',
                'g-funk',
                'future funk',
                'synth-funk',
                'new jack swing'
            ],
            'Disco': [
                'disco',
                'nu-disco',
                'disco house',
                'disco polo',
                'space disco',
                'cosmic disco',
                'italo disco',
                'euro disco',
                'french disco',
                'post-disco',
                'boogie',
                'electro-disco'
            ],
            'Synthwave': [
                'synthwave',
                'outrun',
                'darksynth',
                'dreamwave',
                'chillwave',
                'retrowave',
                'vaporwave',
                'future funk',
                'spacewave',
                'cybersynth',
                'sovietwave',
                'mallsoft'
            ]
        }
    
    def _build_reverse_mapping(self) -> Dict[str, str]:
        reverse_map = {}
        for parent, children in self.taxonomy.items():
            for child in children:
                reverse_map[child.lower()] = parent
        return reverse_map
    
    def get_parent_genre(self, subgenre: str) -> Optional[str]:
        subgenre_lower = subgenre.lower()
        
        parent = self.subgenre_to_parent.get(subgenre_lower)
        if parent:
            return parent
        
        for normalized_subgenre, parent in self.subgenre_to_parent.items():
            if subgenre_lower in normalized_subgenre or normalized_subgenre in subgenre_lower:
                return parent
        
        return None
    
    def should_aggregate(self, genre: str) -> bool:
        return self.get_parent_genre(genre) is not None
    
    def get_all_parent_genres(self) -> Set[str]:
        return set(self.taxonomy.keys())
    
    def get_subgenres_for_parent(self, parent: str) -> List[str]:
        return self.taxonomy.get(parent, [])
    
    def is_cultural_variant(self, genre: str) -> bool:
        cultural_prefixes = ['k-', 'j-', 'c-', 'mandopop', 'cantopop', 'britpop']
        genre_lower = genre.lower()
        
        for prefix in cultural_prefixes:
            if genre_lower.startswith(prefix):
                return True
        
        cultural_genres = {
            'k-pop', 'j-pop', 'c-pop', 'j-rock', 'k-indie',
            'mandopop', 'cantopop', 'britpop', 'j-rap', 'k-r&b'
        }
        return genre_lower in cultural_genres
    
    def normalize_genre_for_display(self, genre: str) -> str:
        parent = self.get_parent_genre(genre)
        if parent:
            return parent
        
        if self.is_cultural_variant(genre):
            return genre.title()
        
        return genre.title()
    
    def get_genre_hierarchy_info(self, genre: str) -> Dict[str, any]:
        parent = self.get_parent_genre(genre)
        is_parent = genre in self.taxonomy
        is_cultural = self.is_cultural_variant(genre)
        
        return {
            'original': genre,
            'parent': parent,
            'display_name': self.normalize_genre_for_display(genre),
            'is_parent': is_parent,
            'is_cultural_variant': is_cultural,
            'should_aggregate': parent is not None
        }

GENRE_TAXONOMY = GenreTaxonomy()
