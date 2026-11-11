"""Реальные составы клубов (сезон 2026/27) - добавляются в data/real_players.csv как известные игроки (tier = notable).

    python tools/real_squads.py

Состав клуба = игроки, которые уже есть в real_players.csv (звёзды, перспективные, известные) + игроки отсюда; игрок, который
уже есть в файле (под любым клубом), второй раз не добавляется. Остальная часть заявки генерируется игрой, когда тренер
возглавляет клуб (game/squad.py, build).
Возраст - в сезоне 2026/27, OVR - в шкале EA FC. Потенциал считается по возрасту: у 23 лет и моложе - вилка выше нынешнего OVR.
Составы собраны по данным до лета 2026 года (летние переходы 2026 года могли пройти мимо), арендованные игроки - в своих клубах.
Строка игрока: "Имя;сборная;позиция;возраст;OVR".
"""
import csv, sqlite3, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "real_players.csv"

SQUADS = {
# ------------------------------------------------------------------ Англия, Премьер-лига
"eng-afc-bournemouth": """
Đorđe Petrović;SRB;GK;27;78
Will Dennis;ENG;GK;26;66
Adam Smith;ENG;RB;35;72
Álex Jiménez;ESP;RB;21;74
Julio Soler;ARG;LB;21;73
Adrien Truffert;FRA;LB;24;77
James Hill;ENG;CB;22;72
Bafodé Diakité;FRA;CB;25;77
Veljko Milosavljević;SRB;CB;19;70
Lewis Cook;ENG;CM;29;77
Ryan Christie;SCO;CM;31;76
Hamed Traorè;CIV;CAM;26;74
Marcus Tavernier;ENG;LM;27;78
David Brooks;WAL;RW;29;75
Justin Kluivert;NED;LW;27;80
Amine Adli;MAR;RW;26;77
Enes Ünal;TUR;ST;29;74
""",
"eng-aston-villa": """
Marco Bizot;NED;GK;35;75
Lucas Digne;FRA;LB;33;77
Ian Maatsen;NED;LB;24;78
Tyrone Mings;ENG;CB;33;77
Victor Lindelöf;SWE;CB;32;76
Andrés García;ESP;RB;23;73
Lamare Bogarde;NED;CDM;22;72
Ross Barkley;ENG;CAM;32;76
Emiliano Buendía;ARG;CAM;29;78
Harvey Elliott;ENG;CAM;23;77
Jadon Sancho;ENG;LW;26;78
Donyell Malen;NED;ST;27;79
Evann Guessand;CIV;ST;25;77
""",
"eng-brentford-fc": """
Caoimhín Kelleher;IRL;GK;28;80
Hákon Valdimarsson;ISL;GK;25;70
Aaron Hickey;SCO;RB;24;74
Michael Kayode;ITA;RB;22;75
Rico Henry;ENG;LB;29;74
Keane Lewis-Potter;ENG;LB;25;75
Kristoffer Ajer;NOR;CB;28;76
Sepp van den Berg;NED;CB;24;77
Ethan Pinnock;ENG;CB;33;75
Mathias Jensen;DEN;CM;30;76
Vitaly Janelt;GER;CDM;28;76
Yehor Yarmolyuk;UKR;CM;22;74
Jordan Henderson;ENG;CM;36;76
Fábio Carvalho;POR;CAM;24;75
Antoni Milambo;NED;CAM;21;74
Dango Ouattara;BFA;RW;24;78
Reiss Nelson;ENG;LW;26;74
""",
"eng-brighton-hove-albion": """
Jason Steele;ENG;GK;35;71
Joël Veltman;NED;RB;34;75
Mats Wieffer;NED;RB;27;77
Maxim De Cuyper;BEL;LB;25;78
Ferdi Kadıoğlu;TUR;LB;26;78
Lewis Dunk;ENG;CB;34;78
Olivier Boscagli;FRA;CB;28;76
Diego Coppola;ITA;CB;22;74
Yasin Ayari;SWE;CM;22;76
Jack Hinshelwood;ENG;CM;21;75
Diego Gómez;PAR;CM;23;76
Solly March;ENG;RM;32;75
Brajan Gruda;GER;RW;22;75
Danny Welbeck;ENG;ST;35;76
Stefanos Tzimas;GRE;ST;20;72
Charalampos Kostoulas;GRE;ST;19;71
""",
"eng-coventry-city": """
Carl Rushworth;ENG;GK;25;74
Oliver Dovin;SWE;GK;24;68
Milan van Ewijk;NED;RB;26;75
Kaine Kesler-Hayden;ENG;RB;24;70
Jay Dasilva;WAL;LB;28;73
Jake Bidwell;ENG;LB;33;70
Liam Kitching;ENG;CB;27;74
Bobby Thomas;ENG;CB;25;74
Joel Latibeaudiere;JAM;CB;26;72
Ben Sheaf;ENG;CDM;28;73
Matt Grimes;ENG;CM;31;74
Victor Torp;DEN;CM;27;73
Josh Eccles;ENG;CM;26;72
Jack Rudoni;ENG;CAM;25;76
Tatsuhiro Sakamoto;JPN;RW;29;74
Ephron Mason-Clark;ENG;LW;26;73
Haji Wright;USA;ST;28;76
Ellis Simms;ENG;ST;25;73
Brandon Thomas-Asante;GHA;ST;27;73
""",
"eng-crystal-palace": """
Walter Benítez;ARG;GK;33;74
Chris Richards;USA;CB;26;78
Maxence Lacroix;FRA;CB;26;80
Jaydee Canvot;FRA;CB;20;72
Tyrick Mitchell;ENG;LB;27;77
Borna Sosa;CRO;LB;28;74
Nathaniel Clyne;ENG;RB;35;71
Jefferson Lerma;COL;CDM;31;77
Will Hughes;ENG;CM;31;76
Justin Devenny;NIR;CM;22;71
Daichi Kamada;JPN;CAM;30;77
Romain Esse;ENG;RW;21;72
Eddie Nketiah;ENG;ST;27;76
Christantus Uche;NGA;ST;23;74
""",
"eng-everton-fc": """
Mark Travers;IRL;GK;27;74
Jake O'Brien;IRL;CB;25;77
Michael Keane;ENG;CB;33;76
Vitalii Mykolenko;UKR;LB;27;77
Adam Aznou;MAR;LB;20;70
Nathan Patterson;SCO;RB;25;74
Idrissa Gana Gueye;SEN;CDM;37;76
James Garner;ENG;CM;25;78
Tim Iroegbunam;ENG;CM;23;72
Carlos Alcaraz;ARG;CM;23;75
Merlin Röhl;GER;CAM;24;72
Harrison Armstrong;ENG;CM;19;68
Dwight McNeil;ENG;LW;27;77
Tyler Dibling;ENG;RW;20;74
Beto;GNB;ST;28;75
""",
"eng-fulham-fc": """
Benjamin Lecomte;FRA;GK;35;72
Kenny Tete;NED;RB;31;76
Timothy Castagne;BEL;RB;31;76
Joachim Andersen;DEN;CB;30;79
Calvin Bassey;NGA;CB;26;78
Issa Diop;FRA;CB;29;76
Jorge Cuenca;ESP;CB;27;74
Ryan Sessegnon;ENG;LB;26;74
Sander Berge;NOR;CDM;28;78
Saša Lukić;SRB;CM;30;76
Harrison Reed;ENG;CM;31;74
Tom Cairney;SCO;CM;35;73
Josh King;ENG;CAM;19;70
Harry Wilson;WAL;RW;29;78
Samuel Chukwueze;NGA;RW;27;77
Adama Traoré;ESP;RW;30;75
Kevin;BRA;LW;23;75
Raúl Jiménez;MEX;ST;35;76
Rodrigo Muniz;BRA;ST;25;76
""",
"eng-hull-city": """
Ivor Pandur;CRO;GK;26;73
Dillon Phillips;ENG;GK;31;68
Lewie Coyle;ENG;RB;30;71
Cody Drameh;ENG;RB;24;71
Ryan Giles;ENG;LB;26;73
Charlie Hughes;ENG;CB;23;72
John Egan;IRL;CB;33;72
Semi Ajayi;NGA;CB;32;72
Akin Famewo;ENG;CB;27;70
Regan Slater;ENG;CM;26;72
Matt Crooks;ENG;CM;32;72
Amir Hadžiahmetović;BIH;CM;29;73
John Lundstram;ENG;CDM;32;73
Mohamed Belloumi;ALG;RW;24;72
Abu Kamara;ENG;RW;23;72
Liam Millar;CAN;LW;27;72
Kyle Joseph;SCO;ST;24;72
Oli McBurnie;SCO;ST;30;73
Joe Gelhardt;ENG;ST;24;72
""",
"eng-ipswich-town": """
Alex Palmer;ENG;GK;29;75
Christian Walton;ENG;GK;31;69
Ben Johnson;ENG;RB;26;73
Darnell Furlong;ENG;RB;30;72
Leif Davis;ENG;LB;26;76
Dara O'Shea;IRL;CB;27;76
Jacob Greaves;ENG;CB;26;75
Cédric Kipré;CIV;CB;29;73
Luke Woolfenden;ENG;CB;27;73
Azor Matusiwa;NED;CDM;28;75
Jens Cajuste;SWE;CM;27;75
Jack Taylor;IRL;CM;28;73
Marcelino Núñez;CHI;CM;26;74
Sammie Szmodics;IRL;CAM;30;73
Jaden Philogene;ENG;LW;24;75
Jack Clarke;ENG;LW;25;75
Kasey McAteer;ENG;RW;24;72
Wes Burns;WAL;RW;31;71
Chuba Akpom;ENG;ST;30;73
George Hirst;SCO;ST;27;73
Iván Azón;ESP;ST;23;73
""",
"eng-leeds-united": """
Karl Darlow;WAL;GK;35;70
Illan Meslier;FRA;GK;26;75
Jayden Bogle;ENG;RB;26;76
James Justin;ENG;RB;28;76
Gabriel Gudmundsson;SWE;LB;27;75
Joe Rodon;WAL;CB;28;77
Pascal Struijk;NED;CB;27;76
Jaka Bijol;SVN;CB;27;78
Sebastiaan Bornauw;BEL;CB;27;74
Sean Longstaff;ENG;CM;28;76
Anton Stach;GER;CM;27;77
Ilia Gruev;BUL;CM;26;74
Ao Tanaka;JPN;CM;28;76
Brenden Aaronson;USA;CAM;25;76
Daniel James;WAL;LW;28;76
Wilfried Gnonto;ITA;LW;22;75
Noah Okafor;SUI;LW;26;77
Jack Harrison;ENG;LW;29;74
Lukas Nmecha;GER;ST;27;75
Joël Piroe;NED;ST;27;75
""",
"eng-manchester-united": """
Altay Bayındır;TUR;GK;28;74
Noussair Mazraoui;MAR;RB;28;79
Luke Shaw;ENG;LB;31;78
Harry Maguire;ENG;CB;33;78
Ayden Heaven;ENG;CB;20;72
Casemiro;BRA;CDM;34;79
Joshua Zirkzee;NED;ST;25;77
""",
"eng-newcastle-united": """
Aaron Ramsdale;ENG;GK;28;78
Kieran Trippier;ENG;RB;36;77
Emil Krafth;SWE;RB;32;72
Lewis Hall;ENG;LB;22;79
Dan Burn;ENG;CB;34;78
Fabian Schär;SUI;CB;34;79
Lewis Miley;ENG;CM;20;74
Joe Willock;ENG;CM;27;76
Jacob Ramsey;ENG;CAM;25;77
Harvey Barnes;ENG;LW;28;78
Jacob Murphy;ENG;RW;31;78
Anthony Elanga;SWE;RW;24;79
William Osula;DEN;ST;23;74
""",
"eng-nottingham-forest": """
John Victor;BRA;GK;30;75
Neco Williams;WAL;RB;25;78
Ola Aina;NGA;RB;30;79
Nicolò Savona;ITA;RB;23;75
Jair Cunha;BRA;CB;21;74
Morato;BRA;CB;25;75
Willy Boly;CIV;CB;35;73
Ibrahim Sangaré;CIV;CDM;29;78
Nicolás Domínguez;ARG;CM;28;77
Douglas Luiz;BRA;CM;28;78
James McAtee;ENG;CAM;23;76
Callum Hudson-Odoi;ENG;LW;25;79
Omari Hutchinson;ENG;RW;23;77
Dan Ndoye;SUI;RW;26;79
Dilane Bakwa;FRA;RW;24;76
Igor Jesus;BRA;ST;25;77
Arnaud Kalimuendo;FRA;ST;24;77
""",
"eng-sunderland-afc": """
Anthony Patterson;ENG;GK;26;72
Trai Hume;NIR;RB;24;75
Lutsharel Geertruida;NED;RB;26;77
Reinildo Mandava;MOZ;LB;32;76
Dennis Cirkin;ENG;LB;24;72
Arthur Masuaku;COD;LB;32;73
Daniel Ballard;NIR;CB;26;75
Omar Alderete;PAR;CB;29;77
Nordi Mukiele;FRA;CB;28;77
Luke O'Nien;ENG;CB;31;73
Enzo Le Fée;FRA;CM;26;77
Dan Neil;ENG;CM;24;73
Chris Rigg;ENG;CM;19;72
Simon Adingra;CIV;LW;24;76
Bertrand Traoré;BFA;RW;31;75
Eliezer Mayenda;ESP;ST;21;72
Wilson Isidor;FRA;ST;25;75
Brian Brobbey;NED;ST;24;77
""",
"eng-tottenham-hotspur": """
Antonín Kinský;CZE;GK;23;74
Kevin Danso;AUT;CB;28;79
Radu Drăgușin;ROU;CB;24;76
Ben Davies;WAL;LB;33;75
Djed Spence;ENG;RB;26;77
Yves Bissouma;MLI;CDM;30;78
Wilson Odobert;FRA;LW;21;76
Dejan Kulusevski;SWE;RW;26;82
""",
# ------------------------------------------------------------------ Испания, Ла Лига
"esp-athletic-bilbao": """
Álex Padilla;MEX;GK;23;72
Jesús Areso;ESP;RB;27;77
Andoni Gorosabel;ESP;RB;30;76
Yuri Berchiche;ESP;LB;36;75
Adama Boiro;ESP;LB;23;73
Aymeric Laporte;ESP;CB;32;80
Yeray Álvarez;ESP;CB;31;76
Aitor Paredes;ESP;CB;26;77
Mikel Jauregizar;ESP;CDM;22;77
Beñat Prados;ESP;CM;25;77
Mikel Vesga;ESP;CM;33;75
Iñigo Ruiz de Galarreta;ESP;CM;33;77
Unai Gómez;ESP;CAM;23;74
Álex Berenguer;ESP;LW;31;77
Robert Navarro;ESP;LW;24;75
Nico Serrano;ESP;LW;23;72
Gorka Guruzeta;ESP;ST;30;77
Maroan Sannadi;ESP;ST;25;74
""",
"esp-atletico-de-madrid": """
Juan Musso;ARG;GK;32;78
Clément Lenglet;FRA;CB;31;78
Matteo Ruggeri;ITA;LB;24;78
Nahuel Molina;ARG;RB;28;79
Javi Galán;ESP;LB;31;76
Marc Pubill;ESP;RB;23;77
Nicolás González;ARG;LW;28;80
Giacomo Raspadori;ITA;ST;26;79
""",
"esp-ca-osasuna": """
Sergio Herrera;ESP;GK;33;77
Aitor Fernández;ESP;GK;35;72
Valentin Rosier;FRA;RB;30;75
Abel Bretones;ESP;LB;26;75
Juan Cruz;ESP;LB;33;72
Alejandro Catena;ESP;CB;31;77
Jorge Herrando;ESP;CB;25;74
Enzo Boyomo;CMR;CB;25;75
Lucas Torró;ESP;CDM;32;76
Jon Moncayola;ESP;CM;28;77
Iker Muñoz;ESP;CM;24;73
Aimar Oroz;ESP;CAM;25;77
Rubén García;ESP;LW;33;75
Moi Gómez;ESP;LM;32;74
Kike Barja;ESP;RW;29;73
Víctor Muñoz;ESP;LW;23;76
Raúl García de Haro;ESP;ST;26;74
""",
"esp-celta-de-vigo": """
Iván Villar;ESP;GK;29;76
Ionuț Radu;ROU;GK;29;76
Óscar Mingueza;ESP;RB;27;80
Javi Rueda;ESP;RB;24;74
Sergio Carreira;ESP;RB;26;76
Marcos Alonso;ESP;CB;35;77
Carl Starfelt;SWE;CB;31;78
Carlos Domínguez;ESP;CB;25;77
Joseph Aidoo;GHA;CB;31;75
Manu Fernández;ESP;CB;25;74
Ilaix Moriba;GUI;CM;23;78
Fran Beltrán;ESP;CM;27;78
Hugo Sotelo;ESP;CM;22;75
Damián Rodríguez;ESP;CM;22;73
Miguel Román;ESP;CDM;23;74
Williot Swedberg;SWE;CAM;22;76
Bryan Zaragoza;ESP;LW;25;79
Hugo Álvarez;ESP;LW;23;75
Iago Aspas;ESP;ST;39;78
Ferran Jutglà;ESP;ST;27;77
Pablo Durán;ESP;ST;25;74
""",
"esp-deportivo-a-coruna": """
Germán Parreño;ESP;GK;33;73
Helton Leite;BRA;GK;36;71
Ximo Navarro;ESP;RB;36;71
Pablo Vázquez;ESP;CB;32;73
Dani Barcia;ESP;CB;22;72
Lucas Noubi;BEL;CB;21;71
Charlie Patiño;ENG;CM;22;75
José Ángel;ESP;CM;22;73
Diego Villares;ESP;CM;30;74
Mario Soriano;ESP;CAM;24;77
Yeremay Hernández;ESP;LW;24;79
David Mella;ESP;RW;20;75
Luismi Cruz;ESP;RW;25;75
Zakaria Eddahchouri;NED;ST;25;74
Stoichkov;ESP;ST;32;74
Mohamed Bouldini;MAR;ST;30;73
""",
"esp-deportivo-alaves": """
Antonio Sivera;ESP;GK;30;76
Jonny Otto;ESP;RB;32;74
Víctor Parada;ESP;LB;24;72
Nahuel Tenaglia;ARG;CB;30;76
Facundo Garcés;ARG;CB;27;75
Moussa Diarra;MLI;CB;25;73
Antonio Blanco;ESP;CDM;26;76
Ander Guevara;ESP;CM;29;74
Jon Guridi;ESP;CM;31;75
Carles Aleñá;ESP;CM;28;74
Denis Suárez;ESP;CAM;32;75
Carlos Vicente;ESP;RW;27;75
Abde Rebbach;ALG;LW;28;74
Toni Martínez;ESP;ST;29;75
Lucas Boyé;ARG;ST;30;76
Mariano Díaz;DOM;ST;33;72
""",
"esp-elche-cf": """
Iñaki Peña;ESP;GK;27;74
Álvaro Núñez;ESP;RB;26;74
Héctor Fort;ESP;RB;20;72
Adrià Pedrosa;ESP;LB;28;74
Pedro Bigas;ESP;CB;36;72
David Affengruber;AUT;CB;25;75
Víctor Chust;ESP;CB;26;74
Léo Petrot;FRA;CB;29;72
Marc Aguado;ESP;CM;26;75
Aleix Febas;ESP;CM;30;75
Martim Neto;POR;CM;23;72
Rodrigo Mendoza;ESP;CM;21;74
Germán Valera;ESP;RW;24;74
Josan;ESP;RW;36;71
Yago Santiago;ESP;LW;23;72
Rafa Mir;ESP;ST;29;74
André Silva;POR;ST;30;75
Álvaro Rodríguez;URU;ST;22;73
""",
"esp-getafe-cf": """
David Soria;ESP;GK;33;77
Jiří Letáček;CZE;GK;27;70
Juan Iglesias;ESP;RB;28;75
Diego Rico;ESP;LB;33;75
Djené;TOG;CB;34;77
Domingos Duarte;POR;CB;31;76
Abdel Abqar;MAR;CB;27;75
Zaid Romero;ARG;CB;26;72
Mauro Arambarri;URU;CM;30;77
Luis Milla;ESP;CM;31;78
Mario Martín;ESP;CM;22;74
Javier Muñoz;ESP;CM;31;72
Coba da Costa;POR;LW;23;72
Adrián Liso;ESP;RW;21;73
Álex Sancris;ESP;LW;26;70
Borja Mayoral;ESP;ST;29;76
Juanmi;ESP;ST;33;73
""",
"esp-levante-ud": """
Mathew Ryan;AUS;GK;34;75
Pablo Cuñat;ESP;GK;25;68
Jeremy Toljan;GER;RB;32;72
Manu Sánchez;ESP;LB;26;74
Diego Pampín;ESP;LB;25;72
Unai Elgezabal;ESP;CB;32;73
Adrián de la Fuente;ESP;CB;27;72
Matías Moreno;ARG;CB;22;73
Alan Matturro;URU;CB;21;72
Kervin Arriaga;HON;CDM;28;73
Oriol Rey;ESP;CDM;28;73
Pablo Martínez;ESP;CM;28;74
Unai Vencedor;ESP;CM;25;73
Jon Ander Olasagasti;ESP;CM;25;72
Carlos Álvarez;ESP;CAM;22;76
Roger Brugué;ESP;RW;29;73
Víctor García;ESP;LW;29;71
Iván Romero;ESP;ST;25;74
Karl Etta Eyong;CMR;ST;22;76
Goduine Koyalipou;CTA;ST;26;72
""",
"esp-malaga-cf": """
Alfonso Herrero;ESP;GK;32;73
Carlos Puga;ESP;RB;25;71
Einar Galilea;ESP;CB;31;72
Javier Montero;ESP;CB;27;71
Izan Merino;ESP;CDM;19;71
Dani Lorenzo;ESP;CM;22;73
Luis Muñoz;ESP;CM;29;72
Darko Brašanac;SRB;CM;34;71
David Larrubia;ESP;RW;23;73
Joaquín Muñoz;ESP;LW;25;73
Haitam Abaida;MAR;LW;23;71
Chupe;ESP;ST;23;72
Adrián Niño;ESP;ST;21;72
""",
"esp-rcd-espanyol-barcelona": """
Marko Dmitrović;SRB;GK;34;76
Ángel Fortuño;ESP;GK;24;68
Omar El Hilali;MAR;RB;22;75
Rubén Sánchez;ESP;RB;25;72
Carlos Romero;ESP;LB;24;76
José Salinas;ESP;LB;25;70
Leandro Cabrera;URU;CB;35;74
Fernando Calero;ESP;CB;31;74
Clemens Riedel;GER;CB;22;72
Miguel Rubio;ESP;CB;28;72
Pol Lozano;ESP;CDM;26;75
Urko González de Zárate;ESP;CDM;24;73
Edu Expósito;ESP;CM;30;75
Charles Pickel;SUI;CM;29;73
Ramón Terrats;ESP;CM;26;73
Javi Puado;ESP;LW;28;76
Pere Milla;ESP;LW;33;72
Antoniu Roca;ESP;LW;23;71
Tyrhys Dolan;ENG;RW;25;74
Roberto Fernández;ESP;ST;23;74
""",
"esp-racing-santander": """
Jokin Ezkieta;ESP;GK;30;73
Álvaro Mantilla;ESP;RB;26;72
Mario García;ESP;LB;26;72
Javi Castro;ESP;CB;25;72
Pablo Ramón;ESP;CB;25;71
Aritz Aldasoro;ESP;CM;27;73
Íñigo Sainz-Maza;ESP;CM;28;72
Maguette Gueye;SEN;CM;26;71
Peio Canales;ESP;CAM;21;76
Andrés Martín;ESP;LW;27;76
Iñigo Vicente;ESP;LW;28;76
Juan Carlos Arana;ESP;ST;26;74
Asier Villalibre;ESP;ST;28;73
""",
"esp-rayo-vallecano": """
Augusto Batalla;ARG;GK;30;78
Dani Cárdenas;ESP;GK;28;73
Andrei Rațiu;ROU;RB;28;79
Iván Balliu;ALB;RB;34;75
Pep Chavarría;ESP;LB;28;77
Florian Lejeune;FRA;CB;35;77
Abdul Mumin;GHA;CB;28;75
Luiz Felipe;ITA;CB;29;76
Nobel Mendy;SEN;CB;21;74
Óscar Valentín;ESP;CDM;32;77
Pathé Ciss;SEN;CDM;32;77
Unai López;ESP;CM;30;77
Pedro Díaz;ESP;CM;28;75
Jorge de Frutos;ESP;RW;29;79
Álvaro García;ESP;LW;33;77
Fran Pérez;ESP;RW;23;74
Alemão;BRA;ST;28;76
Sergio Camello;ESP;ST;25;75
Randy Nteka;FRA;ST;28;74
""",
"esp-real-betis-balompie": """
Pau López;ESP;GK;31;79
Álvaro Valles;ESP;GK;29;75
Héctor Bellerín;ESP;RB;31;77
Aitor Ruibal;ESP;RB;30;76
Ángel Ortiz;ESP;RB;22;72
Ricardo Rodríguez;SUI;LB;34;77
Junior Firpo;DOM;LB;30;76
Diego Llorente;ESP;CB;33;77
Marc Bartra;ESP;CB;35;75
Natan;BRA;CB;25;77
Valentín Gómez;ARG;CB;23;75
Marc Roca;ESP;CDM;29;78
Sofyan Amrabat;MAR;CDM;30;79
Pablo Fornals;ESP;CM;30;79
Sergi Altimira;ESP;CM;25;76
Abde Ezzalzouli;MAR;LW;24;80
Rodrigo Riquelme;ESP;LW;26;77
Chimy Ávila;ARG;ST;32;75
""",
"esp-real-sociedad": """
Unai Marrero;ESP;GK;25;72
Jon Aramburu;VEN;RB;23;76
Hamari Traoré;MLI;RB;34;74
Sergio Gómez;ESP;LB;25;77
Aihen Muñoz;ESP;LB;29;74
Jon Martín;ESP;CB;20;74
Aritz Elustondo;ESP;CB;32;74
Duje Ćaleta-Car;CRO;CB;30;76
Jon Pacheco;ESP;CB;25;74
Beñat Turrientes;ESP;CM;24;75
Carlos Soler;ESP;CM;29;78
Luka Sučić;CRO;CM;23;78
Jon Gorrotxategi;ESP;CDM;23;74
Pablo Marín;ESP;CM;23;74
Arsen Zakharyan;RUS;CAM;23;76
Ander Barrenetxea;ESP;LW;24;77
Gonçalo Guedes;POR;RW;29;77
Orri Óskarsson;ISL;ST;22;76
Umar Sadiq;NGA;ST;29;74
""",
"esp-sevilla-fc": """
Odisseas Vlachodimos;GRE;GK;32;77
Ørjan Nyland;NOR;GK;36;73
José Ángel Carmona;ESP;RB;24;76
Juanlu Sánchez;ESP;RB;23;75
Gabriel Suazo;CHI;LB;29;75
Kike Salas;ESP;CB;24;75
Tanguy Nianzou;FRA;CB;24;75
Marcão;BRA;CB;30;75
Nemanja Gudelj;SRB;CB;34;76
Andrés Castrín;ESP;CB;22;70
Lucien Agoumé;FRA;CDM;24;76
Djibril Sow;SUI;CM;29;76
Batista Mendy;FRA;CM;26;75
Manu Bueno;ESP;CM;22;72
Peque Fernández;ESP;CAM;24;73
Rubén Vargas;SUI;LW;28;78
Chidera Ejuke;NGA;LW;28;76
Alexis Sánchez;CHI;RW;37;75
Isaac Romero;ESP;ST;26;75
Akor Adams;NGA;ST;26;76
""",
"esp-valencia-cf": """
Stole Dimitrievski;MKD;GK;32;76
Julen Agirrezabala;ESP;GK;25;74
Dimitri Foulquier;FRA;RB;33;73
Thierry Correia;POR;RB;27;74
Jesús Vázquez;ESP;LB;23;74
José Copete;ESP;CB;26;74
César Tárrega;ESP;CB;24;77
Mouctar Diakhaby;GUI;CB;29;76
Eray Cömert;SUI;CB;28;74
Pepelu;ESP;CDM;28;77
Javi Guerra;ESP;CM;23;77
Baptiste Santamaria;FRA;CM;31;75
Filip Ugrinić;SUI;CM;27;74
André Almeida;POR;CAM;26;76
Luis Rioja;ESP;LW;32;76
Arnaut Danjuma;NED;LW;29;76
Diego López;ESP;RW;24;76
Hugo Duro;ESP;ST;26;76
Lucas Beltrán;ARG;ST;25;75
Dani Raba;ESP;ST;31;74
""",
"esp-villarreal-cf": """
Diego Conde;ESP;GK;28;75
Arnau Tenas;ESP;GK;25;72
Santiago Mouriño;URU;RB;24;76
Kiko Femenía;ESP;RB;35;74
Sergi Cardona;ESP;LB;27;76
Alfonso Pedraza;ESP;LB;30;77
Juan Foyth;ARG;CB;28;78
Renato Veiga;POR;CB;23;78
Rafa Marín;ESP;CB;24;77
Logan Costa;CPV;CB;25;76
Willy Kambwala;FRA;CB;22;72
Santi Comesaña;ESP;CM;30;77
Dani Parejo;ESP;CM;37;78
Pape Gueye;SEN;CM;27;78
Thomas Partey;GHA;CDM;33;79
Alberto Moleiro;ESP;CAM;23;78
Tajon Buchanan;CAN;RW;27;76
Ilias Akhomach;MAR;RW;22;75
Ayoze Pérez;ESP;ST;33;79
Tani Oluwaseyi;CAN;ST;26;72
""",
# ------------------------------------------------------------------ Италия, Серия A
"ita-ac-milan": """
Pietro Terracciano;ITA;GK;36;74
Pervis Estupiñán;ECU;LB;28;79
Davide Bartesaghi;ITA;LB;20;74
Zachary Athekame;SUI;RB;22;74
Koni De Winter;BEL;CB;24;77
Matteo Gabbia;ITA;CB;26;78
Alexis Saelemaekers;BEL;RW;27;79
Ruben Loftus-Cheek;ENG;CM;30;78
""",
"ita-ac-monza": """
Semuel Pizzignacco;ITA;GK;24;74
Samuele Birindelli;ITA;RB;27;75
Andrea Carboni;ITA;CB;25;75
Armando Izzo;ITA;CB;34;73
Luca Caldirola;ITA;CB;35;72
Davide Bettella;ITA;CB;26;71
Matteo Pessina;ITA;CM;29;76
Alessandro Bianco;ITA;CM;24;73
Mattia Valoti;ITA;CAM;33;72
Patrick Ciurria;ITA;RW;31;74
Gianluca Caprari;ITA;LW;33;74
Dany Mota;POR;ST;28;76
Andrea Petagna;ITA;ST;31;74
Keita Baldé;SEN;ST;31;74
""",
"ita-acf-fiorentina": """
Oliver Christensen;DEN;GK;27;71
Dodô;BRA;RB;28;79
Robin Gosens;GER;LB;32;78
Fabiano Parisi;ITA;LB;25;75
Luca Ranieri;ITA;CB;27;77
Pietro Comuzzo;ITA;CB;21;76
Marin Pongračić;CRO;CB;29;76
Rolando Mandragora;ITA;CM;29;77
Nicolò Fagioli;ITA;CM;25;78
Simon Sohm;SUI;CM;25;75
Hans Nicolussi Caviglia;ITA;CM;26;75
Amir Richardson;MAR;CM;24;73
Jacopo Fazzini;ITA;CAM;23;74
Roberto Piccoli;ITA;ST;25;76
""",
"ita-as-roma": """
Pierluigi Gollini;ITA;GK;31;74
Zeki Çelik;TUR;RB;29;76
Wesley;BRA;RB;23;78
Angeliño;ESP;LB;29;79
Konstantinos Tsimikas;GRE;LB;30;76
Mario Hermoso;ESP;CB;31;77
Jan Ziółkowski;POL;CB;21;72
Bryan Cristante;ITA;CM;31;78
Neil El Aynaoui;MAR;CM;25;77
Niccolò Pisilli;ITA;CM;22;74
Tommaso Baldanzi;ITA;CAM;23;75
Stephan El Shaarawy;ITA;LW;33;76
""",
"ita-atalanta-bc": """
Francesco Rossi;ITA;GK;35;68
Raoul Bellanova;ITA;RB;26;78
Davide Zappacosta;ITA;RB;34;76
Berat Djimsiti;ALB;CB;33;78
Odilon Kossounou;CIV;CB;25;78
Sead Kolašinac;BIH;CB;33;76
Giorgio Scalvini;ITA;CB;22;79
Honest Ahanor;ITA;CB;18;70
Mario Pašalić;CRO;CM;31;78
Yunus Musah;USA;CM;23;76
Lazar Samardžić;SRB;CAM;24;78
Daniel Maldini;ITA;CAM;24;74
Nicola Zalewski;POL;LW;24;76
Kamaldeen Sulemana;GHA;LW;24;75
""",
"ita-bologna-fc-1909": """
Łukasz Skorupski;POL;GK;35;78
Federico Ravaglia;ITA;GK;27;72
Emil Holm;SWE;RB;26;77
Nadir Zortea;ITA;RB;27;75
Charalampos Lykogiannis;GRE;LB;32;74
Juan Miranda;ESP;LB;26;76
Torbjørn Heggem;NOR;CB;27;75
Nicolò Casale;ITA;CB;28;75
Martin Vitík;CZE;CB;23;74
Remo Freuler;SUI;CM;34;78
Nikola Moro;CRO;CM;28;75
Tommaso Pobega;ITA;CM;27;75
Jens Odgaard;DEN;CAM;27;76
Benjamín Domínguez;ARG;LW;23;75
Jonathan Rowe;ENG;LW;23;77
Federico Bernardeschi;ITA;RW;32;77
Thijs Dallinga;NED;ST;26;75
Ciro Immobile;ITA;ST;36;75
""",
"ita-cagliari-calcio": """
Elia Caprile;ITA;GK;25;76
Alen Sherri;ALB;GK;28;66
Gabriele Zappa;ITA;RB;27;74
Marco Palestra;ITA;RB;21;75
Adam Obert;SVK;LB;24;72
Yerry Mina;COL;CB;32;75
Sebastiano Luperto;ITA;CB;29;75
Juan Rodríguez;URU;CB;21;70
Michel Adopo;FRA;CM;26;74
Alessandro Deiola;ITA;CM;31;73
Matteo Prati;ITA;CM;22;73
Michael Folorunsho;ITA;CM;28;75
Luca Mazzitelli;ITA;CM;31;72
Gianluca Gaetano;ITA;CAM;26;75
Mattia Felici;ITA;LW;25;72
Sebastiano Esposito;ITA;ST;24;74
Andrea Belotti;ITA;ST;32;73
""",
"ita-como-1907": """
Mauro Vigorito;ITA;GK;36;66
Mergim Vojvoda;KOS;RB;31;74
Ivan Smolčić;CRO;RB;26;74
Álex Valle;ESP;LB;22;75
Marc-Oliver Kempf;GER;CB;31;76
Diego Carlos;BRA;CB;33;76
Jacobo Ramón;ESP;CB;21;74
Edoardo Goldaniga;ITA;CB;32;72
Lucas Da Cunha;FRA;CM;25;77
Sergi Roberto;ESP;CM;34;75
Martin Baturina;CRO;CAM;23;78
Nicolas Kühn;GER;LW;26;77
Jayden Addai;NED;RW;20;73
Anastasios Douvikas;GRE;ST;27;76
Álvaro Morata;ESP;ST;34;77
""",
"ita-frosinone-calcio": """
Michele Cerofolini;ITA;GK;27;71
Anthony Oyono;GAB;LB;25;71
Ilario Monterisi;ITA;CB;25;70
Francesco Gelli;ITA;CM;29;71
Giorgi Kvernadze;GEO;LW;23;73
Farès Ghedjemis;FRA;RW;23;72
""",
"ita-genoa-cfc": """
Justin Bijlow;NED;GK;28;76
Nicola Leali;ITA;GK;33;72
Brooke Norton-Cuffy;ENG;RB;22;75
Aarón Martín;ESP;LB;29;76
Leo Østigård;NOR;CB;26;76
Johan Vásquez;MEX;CB;27;78
Alessandro Marcandalli;ITA;CB;23;72
Sebastian Otoa;DEN;CB;22;71
Morten Frendrup;DEN;CM;25;77
Patrizio Masini;ITA;CM;25;73
Morten Thorsby;NOR;CM;30;74
Mikael Ellertsson;ISL;CM;24;72
Ruslan Malinovskyi;UKR;CAM;33;75
Albert Grønbæk;DEN;CAM;25;72
Junior Messias;BRA;RW;35;72
Vítor Oliveira;POR;ST;26;75
Lorenzo Colombo;ITA;ST;24;74
Caleb Ekuban;GHA;ST;32;72
Jeff Ekhator;ITA;ST;19;70
""",
"ita-inter-milan": """
Josep Martínez;ESP;GK;28;77
Carlos Augusto;BRA;LB;27;79
Matteo Darmian;ITA;RB;36;75
Stefan de Vrij;NED;CB;34;79
Petar Sučić;CRO;CM;23;77
Andy Diouf;FRA;CM;23;76
Luis Henrique;BRA;RW;24;77
""",
"ita-juventus-fc": """
Mattia Perin;ITA;GK;33;76
João Mário;POR;RB;26;75
Juan Cabal;COL;LB;25;75
Pierre Kalulu;FRA;CB;26;79
Federico Gatti;ITA;CB;28;78
Lloyd Kelly;ENG;CB;28;77
Weston McKennie;USA;CM;28;78
Fabio Miretti;ITA;CM;23;75
Vasilije Adžić;MNE;CM;20;70
Edon Zhegrova;KOS;RW;27;79
""",
"ita-parma-calcio-1913": """
Zion Suzuki;JPN;GK;24;77
Edoardo Corvi;ITA;GK;25;68
Enrico Delprato;ITA;RB;26;75
Emanuele Valeri;ITA;LB;28;74
Alessandro Circati;AUS;CB;23;75
Mariano Troilo;ARG;CB;23;72
Abdoulaye Ndiaye;SEN;CB;24;73
Lautaro Valenti;ARG;CB;27;73
Adrián Bernabé;ESP;CM;25;77
Nahuel Estévez;ARG;CM;31;74
Mandela Keita;BEL;CDM;24;75
Hernani;BRA;CM;32;72
Christian Ordóñez;ARG;CM;22;71
Gaetano Oristanio;ITA;RW;24;74
Pontus Almqvist;SWE;RW;27;73
Mateo Pellegrino;ARG;ST;24;75
Patrick Cutrone;ITA;ST;28;74
""",
"ita-ss-lazio": """
Christos Mandas;GRE;GK;25;77
Adam Marušić;MNE;RB;34;76
Manuel Lazzari;ITA;RB;33;75
Nuno Tavares;POR;LB;26;77
Luca Pellegrini;ITA;LB;27;74
Mario Gila;ESP;CB;26;79
Samuel Gigot;FRA;CB;33;74
Oliver Provstgaard;DEN;CB;23;72
Toma Bašić;CRO;CM;30;73
Danilo Cataldi;ITA;CDM;32;75
Matías Vecino;URU;CM;35;74
Reda Belahyane;MAR;CM;22;72
Fisayo Dele-Bashiru;NGA;CM;25;74
Gustav Isaksen;DEN;RW;25;77
Mattéo Cancellieri;ITA;RW;24;74
Boulaye Dia;SEN;ST;30;76
Tijjani Noslin;NED;ST;27;74
""",
"ita-ssc-napoli": """
Vanja Milinković-Savić;SRB;GK;29;79
Mathías Olivera;URU;LB;29;79
Leonardo Spinazzola;ITA;LB;33;76
Miguel Gutiérrez;ESP;LB;25;78
Pasquale Mazzocchi;ITA;RB;31;73
Sam Beukema;NED;CB;28;79
Juan Jesus;BRA;CB;35;74
Billy Gilmour;SCO;CM;25;78
Matteo Politano;ITA;RW;33;78
Lorenzo Lucca;ITA;ST;26;76
""",
"ita-torino-fc": """
Franco Israel;URU;GK;26;74
Alberto Paleari;ITA;GK;34;72
Marcus Pedersen;NOR;RB;26;74
Valentino Lazaro;AUT;RB;30;74
Cristiano Biraghi;ITA;LB;34;73
Ardian Ismajli;ALB;CB;30;75
Guillermo Maripán;CHI;CB;32;75
Adam Masina;MAR;CB;32;72
Kristjan Asllani;ALB;CDM;24;75
Gvidas Gineitis;LTU;CM;22;73
Cesare Casadei;ITA;CM;23;74
Adrien Tameze;FRA;CM;32;73
Nikola Vlašić;CRO;CAM;29;77
Cyril Ngonge;BEL;LW;26;74
Zakaria Aboukhlal;MAR;RW;26;74
Giovanni Simeone;ARG;ST;31;75
Che Adams;SCO;ST;30;75
""",
"ita-us-lecce": """
Wladimiro Falcone;ITA;GK;31;77
Danilo Veiga;POR;RB;24;72
Antonino Gallo;ITA;LB;26;74
Kialonda Gaspar;ANG;CB;29;74
Tiago Gabriel;POR;CB;21;72
Jamil Siebert;GER;CB;24;70
Ylber Ramadani;ALB;CDM;30;74
Lassana Coulibaly;MLI;CM;30;73
Medon Berisha;ALB;CM;23;70
Mohamed Kaba;FRA;CM;25;71
Riccardo Sottil;ITA;LW;27;73
Lameck Banda;ZAM;LW;25;73
Santiago Pierotti;ARG;RW;25;72
Konan N'Dri;CIV;RW;26;71
Nikola Štulić;SRB;ST;24;72
""",
"ita-us-sassuolo": """
Arijanet Muric;KOS;GK;27;75
Woyo Coulibaly;MLI;RB;27;72
Josh Doig;SCO;LB;24;74
Sebastian Walukiewicz;POL;CB;26;74
Jay Idzes;IDN;CB;26;75
Tarik Muharemović;BIH;CB;23;74
Filippo Romagna;ITA;CB;29;72
Kristian Thorstvedt;NOR;CM;27;75
Daniel Boloca;ROU;CM;27;73
Aster Vranckx;BEL;CM;23;73
Luca Lipani;ITA;CM;21;72
Cristian Volpato;AUS;CAM;22;72
Domenico Berardi;ITA;RW;32;78
Armand Laurienté;FRA;LW;28;78
Andrea Pinamonti;ITA;ST;27;76
Walid Cheddira;MAR;ST;28;73
""",
"ita-udinese-calcio": """
Maduka Okoye;NGA;GK;26;76
Kingsley Ehizibue;NED;RB;31;73
Hassane Kamara;CIV;LB;32;74
Jordan Zemura;ZIM;LB;26;73
Thomas Kristensen;DEN;CB;24;75
Oumar Solet;FRA;CB;26;77
Christian Kabasele;BEL;CB;35;73
Nicolò Bertola;ITA;CB;23;72
Jesper Karlström;SWE;CM;30;75
Jakub Piotrowski;POL;CM;28;74
Arthur Atta;FRA;CM;23;75
Lennon Miller;SCO;CM;19;71
Sandi Lovrić;SVN;CM;28;74
Jurgen Ekkelenkamp;NED;CM;26;75
Nicolò Zaniolo;ITA;CAM;27;76
Keinan Davis;ENG;ST;28;75
Iker Bravo;ESP;ST;21;72
Adam Buksa;POL;ST;30;73
""",
"ita-venezia-fc": """
Filip Stanković;SRB;GK;24;75
Antonio Candela;ITA;RB;26;72
Ridgeciano Haps;SUR;LB;33;72
Michael Svoboda;AUT;CB;27;73
Joel Schingtienne;BEL;CB;23;72
Gianluca Busio;USA;CM;24;75
Issa Doumbia;ITA;CM;22;72
Alfred Duncan;GHA;CM;33;72
John Yeboah;ECU;LW;26;74
Andrea Adorante;ITA;ST;25;73
""",
# ------------------------------------------------------------------ Германия, Бундеслига
"ger-bayern-munich": """
Jonas Urbig;GER;GK;23;76
Raphaël Guerreiro;POR;LB;32;78
Sacha Boey;FRA;RB;26;76
""",
"ger-borussia-dortmund": """
Alexander Meyer;GER;GK;35;72
Julian Ryerson;NOR;RB;29;79
Yan Couto;BRA;RB;24;77
Daniel Svensson;SWE;LB;24;78
Ramy Bensebaini;ALG;LB;31;77
Niklas Süle;GER;CB;31;79
Filippo Mané;ITA;CB;21;70
Pascal Groß;GER;CM;35;78
Carney Chukwuemeka;ENG;CM;22;75
Fábio Silva;POR;ST;24;76
""",
"ger-bayer-04-leverkusen": """
Janis Blaswich;GER;GK;35;74
Lucas Vázquez;ESP;RB;35;77
Arthur;BRA;RB;23;75
Edmond Tapsoba;BFA;CB;27;81
Loïc Badé;FRA;CB;26;80
Jarell Quansah;ENG;CB;23;79
Robert Andrich;GER;CDM;32;80
Aleix García;ESP;CM;29;81
Equi Fernández;ARG;CM;24;77
Jonas Hofmann;GER;CAM;34;77
Nathan Tella;NGA;RW;27;77
Ernest Poku;NED;RW;22;76
Christian Kofane;CMR;ST;20;74
""",
"ger-rb-leipzig": """
Péter Gulácsi;HUN;GK;36;77
Maarten Vandevoordt;BEL;GK;24;77
Lukas Klostermann;GER;RB;30;77
Ridle Baku;GER;RB;28;77
Kosta Nedeljković;SRB;RB;21;73
Castello Lukeba;FRA;CB;23;81
El Chadaille Bitshiabu;FRA;CB;21;75
Xaver Schlager;AUT;CM;28;81
Nicolas Seiwald;AUT;CDM;25;79
Amadou Haidara;MLI;CM;28;77
Kevin Kampl;SVN;CM;35;76
Ezechiel Banzuzi;BEL;CM;21;74
Rômulo;BRA;ST;24;76
Conrad Harder;DEN;ST;21;75
""",
"ger-vfb-stuttgart": """
Fabian Bredlow;GER;GK;31;72
Josha Vagnoman;GER;RB;26;76
Lorenz Assignon;FRA;RB;26;76
Pascal Stenzel;GER;RB;30;74
Jeff Chabot;GER;CB;28;78
Ramon Hendriks;NED;CB;25;76
Luca Jaquez;SUI;CB;23;74
Finn Jeltsch;GER;CB;19;73
Atakan Karazor;GER;CDM;29;77
Chema Andrés;ESP;CM;21;75
Nikolas Nartey;DEN;CM;26;74
Bilal El Khannouss;MAR;CAM;22;78
Chris Führich;GER;LW;28;78
Jamie Leweling;GER;RW;25;79
Badredine Bouanani;FRA;RW;21;73
Tiago Tomás;POR;ST;24;75
""",
"ger-tsg-1899-hoffenheim": """
Luca Philipp;GER;GK;25;70
Vladimír Coufal;CZE;RB;34;76
Bernardo;BRA;LB;31;75
Alexander Prass;AUT;LB;25;76
Ozan Kabak;TUR;CB;26;77
Albian Hajdari;SUI;CB;23;76
Robin Hranáč;CZE;CB;26;76
Kevin Akpoguma;NGA;CB;31;74
Grischa Prömel;GER;CM;31;76
Wouter Burger;NED;CM;25;76
Leon Avdullahu;SUI;CDM;22;74
Muhammed Damar;GER;CAM;22;73
Bazoumana Touré;CIV;LW;20;75
Fisnik Asllani;KOS;ST;23;77
Tim Lemperle;GER;ST;24;76
Adam Hložek;CZE;ST;24;75
Max Moerstedt;GER;ST;20;70
""",
"ger-1-fsv-mainz-05": """
Robin Zentner;GER;GK;31;76
Lasse Rieß;GER;GK;25;68
Danny da Costa;GER;RB;33;74
Silvan Widmer;SUI;RB;33;74
Phillipp Mwene;AUT;RB;32;74
Anthony Caci;FRA;LB;29;75
Stefan Bell;GER;CB;34;74
Dominik Kohr;GER;CB;32;75
Andreas Hanche-Olsen;NOR;CB;29;76
Maxim Leitsch;GER;CB;28;75
Kaishu Sano;JPN;CDM;25;78
Sota Kawasaki;JPN;CM;25;73
Paul Nebel;GER;CAM;24;76
Lee Jae-sung;KOR;CAM;34;76
Benedict Hollerbach;GER;ST;25;75
Armindo Sieb;GER;ST;23;74
Nelson Weiper;GER;ST;21;73
""",
"ger-sc-freiburg": """
Noah Atubolu;GER;GK;24;79
Florian Müller;GER;GK;28;70
Lukas Kübler;GER;RB;34;75
Philipp Treu;GER;RB;25;74
Christian Günter;GER;LB;33;76
Jordy Makengo;FRA;LB;25;74
Matthias Ginter;GER;CB;32;78
Philipp Lienhart;AUT;CB;30;77
Max Rosenfelder;GER;CB;23;75
Bruno Ogbus;SUI;CB;20;71
Maximilian Eggestein;GER;CM;29;77
Nicolas Höfler;GER;CDM;36;73
Johan Manzambi;SUI;CM;21;75
Patrick Osterhage;GER;CM;26;74
Yuito Suzuki;JPN;CAM;24;75
Jan-Niklas Beste;GER;LW;27;76
Derry Scherhant;GER;RW;23;73
Lucas Höler;GER;ST;32;74
Igor Matanović;CRO;ST;23;74
""",
"ger-borussia-monchengladbach": """
Moritz Nicolas;GER;GK;29;75
Jonas Omlin;SUI;GK;32;74
Joe Scally;USA;RB;23;75
Luca Netz;GER;LB;23;74
Lukas Ullrich;GER;LB;22;71
Nico Elvedi;SUI;CB;30;76
Kevin Diks;NED;CB;29;76
Marvin Friedrich;GER;CB;30;73
Rocco Reitz;GER;CM;24;76
Philipp Sander;GER;CDM;28;74
Julian Weigl;GER;CDM;30;75
Florian Neuhaus;GER;CM;29;75
Kevin Stöger;AUT;CAM;33;76
Giovanni Reyna;USA;CAM;23;73
Franck Honorat;FRA;RW;29;76
Robin Hack;GER;LW;28;75
Haris Tabaković;BIH;ST;32;74
Shuto Machino;JPN;ST;27;73
""",
"ger-eintracht-frankfurt": """
Kauã Santos;BRA;GK;23;74
Michael Zetterer;GER;GK;31;72
Rasmus Kristensen;DEN;RB;29;75
Nathaniel Brown;GER;LB;23;74
Arthur Theate;BEL;CB;26;77
Aurèle Amenda;SUI;CB;22;71
Nnamdi Collins;GER;CB;22;71
Ellyes Skhiri;TUN;CDM;31;76
Hugo Larsson;SWE;CM;22;77
Oscar Højlund;DEN;CM;21;71
Fares Chaibi;ALG;CAM;23;75
Ritsu Dōan;JPN;RW;28;77
Ansgar Knauff;GER;RW;24;75
Jean-Mattéo Bahoya;FRA;LW;21;73
Elye Wahi;FRA;ST;23;74
Michy Batshuayi;BEL;ST;32;72
""",
"ger-1-fc-koln": """
Marvin Schwäbe;GER;GK;31;76
Jan Thielmann;GER;RB;24;74
Kristoffer Lund;USA;LB;24;74
Leart Paqarada;KOS;LB;31;74
Timo Hübers;GER;CB;30;75
Joël Schmied;SUI;CB;27;74
Cenk Özkacar;TUR;CB;25;74
Rav van den Berg;NED;CB;21;73
Eric Martel;GER;CDM;24;76
Dejan Ljubičić;AUT;CM;28;75
Tom Krauß;GER;CM;25;74
Isak Bergmann Jóhannesson;ISL;CM;23;76
Linton Maina;GER;LW;27;75
Jakub Kamiński;POL;LW;24;76
Luca Waldschmidt;GER;ST;30;74
Ragnar Ache;GER;ST;28;74
Marius Bülter;GER;ST;33;73
""",
"ger-1-fc-union-berlin": """
Frederik Rønnow;DEN;GK;34;77
Carl Klaus;GER;GK;32;66
Josip Juranović;CRO;RB;31;75
Tom Rothe;GER;LB;21;75
Derrick Köhn;GER;LB;27;73
Diogo Leite;POR;CB;27;77
Danilho Doekhi;NED;CB;28;77
Leopold Querfeld;AUT;CB;22;76
Kevin Vogt;GER;CB;35;72
Rani Khedira;GER;CDM;32;76
Aljoscha Kemlein;GER;CM;22;74
András Schäfer;HUN;CM;27;75
Alex Král;CZE;CM;28;74
Janik Haberer;GER;CM;32;72
Tim Skarke;GER;RW;29;72
Jeong Woo-yeong;KOR;RW;27;73
Andrej Ilić;SRB;ST;26;74
Ilyas Ansah;GER;ST;21;73
Oliver Burke;SCO;ST;29;72
Marin Ljubičić;AUT;ST;24;72
""",
"ger-fc-augsburg": """
Finn Dahmen;GER;GK;28;76
Nediljko Labrović;CRO;GK;27;72
Marius Wolf;GER;RB;31;74
Dimitris Giannoulis;GRE;LB;31;74
Mads Pedersen;DEN;LB;30;73
Jeffrey Gouweleeuw;NED;CB;35;74
Keven Schlotterbeck;GER;CB;29;74
Cédric Zesiger;SUI;CB;28;74
Chrislain Matsima;FRA;CB;24;74
Kristijan Jakić;CRO;CDM;29;75
Han-Noah Massengo;FRA;CM;25;73
Elvis Rexhbeçaj;KOS;CM;29;74
Fabian Rieder;SUI;CAM;24;75
Alexis Claude-Maurice;FRA;CAM;28;75
Anton Kade;GER;LW;22;73
Mert Kömür;GER;RW;21;72
Phillip Tietz;GER;ST;29;73
Samuel Essende;COD;ST;28;73
Steve Mounié;BEN;ST;32;72
""",
"ger-hamburger-sv": """
Daniel Heuer Fernandes;POR;GK;33;74
William Mikelbrencis;FRA;RB;22;72
Miro Muheim;SUI;LB;28;74
Jordan Torunarigha;GER;CB;28;74
Daniel Elfadli;GER;CB;29;73
Nicolás Capaldo;ARG;CDM;27;74
Jonas Meffert;GER;CDM;31;73
Albert Sambi Lokonga;BEL;CM;26;75
Ludovit Reis;NED;CM;26;74
Immanuel Pherai;NED;CAM;25;72
Jean-Luc Dompé;FRA;LW;31;74
Bakery Jatta;GAM;RW;28;73
Yussuf Poulsen;DEN;ST;32;74
Ransford Königsdörffer;GHA;ST;24;73
Robert Glatzel;GER;ST;32;72
Rayan Philippe;LUX;ST;25;72
""",
"ger-sv-werder-bremen": """
Mio Backhaus;GER;GK;22;74
Mitchell Weiser;GER;RB;32;75
Felix Agu;GER;RB;27;74
Olivier Deman;BEL;LB;26;72
Marco Friedl;AUT;CB;28;76
Niklas Stark;GER;CB;31;74
Amos Pieper;GER;CB;28;74
Karim Coulibaly;GER;CB;19;72
Senne Lynen;BEL;CDM;27;76
Jens Stage;DEN;CM;29;77
Leonardo Bittencourt;GER;CM;32;73
Cameron Puertas;SUI;CAM;27;75
Marco Grüll;AUT;LW;28;74
Samuel Mbangula;BEL;LW;22;74
Justin Njinmah;GER;ST;25;74
Keke Topp;GER;ST;22;72
""",
"ger-fc-schalke-04": """
Loris Karius;GER;GK;33;75
Justin Heekeren;GER;GK;25;73
Mehmet Aydın;GER;RB;24;73
Adrian Gantenbein;SUI;RB;25;72
Vitalie Becker;GER;LB;21;72
Nikola Katić;SUI;CB;29;75
Hasan Kurucay;DEN;CB;28;73
Mertcan Ayhan;TUR;CB;23;73
Timo Becker;GER;CB;29;73
Ron Schallenberg;GER;CDM;27;75
Soufiane El-Faouzi;GER;CM;23;72
Christopher Antwi-Adjei;GHA;LW;32;73
Kenan Karaman;TUR;ST;32;75
Moussa Sylla;MLI;ST;26;74
""",
"ger-sc-paderborn-07": """
Dennis Seimen;GER;GK;20;70
Raphael Obermair;AUT;LB;30;70
Calvin Brackelmann;GER;CB;26;70
Felix Götze;GER;CB;28;70
Laurin Curda;GER;CB;21;69
Mattes Hansen;GER;CM;21;70
Santiago Castañeda;USA;CM;22;71
Sebastian Klaas;GER;CM;27;70
Filip Bilbija;BIH;ST;25;72
""",
"ger-sv-07-elversberg": """
Nicolas Kristof;GER;GK;26;71
Lukas Pinckert;GER;RB;26;69
Florian Le Joncour;FRA;CB;30;69
Robin Fellhauer;GER;CM;28;70
Semih Şahin;TUR;CM;26;71
Tom Zimmerschied;GER;LW;26;71
Lasse Günther;GER;LW;23;71
Younes Ebnoutalib;GER;ST;22;73
""",
# ------------------------------------------------------------------ Франция, Лига 1
"fra-as-monaco": """
Philipp Köhn;SUI;GK;28;77
Radosław Majecki;POL;GK;27;74
Vanderson;BRA;RB;25;79
Jordan Teze;NED;RB;26;76
Caio Henrique;BRA;LB;29;78
Kassoum Ouattara;BFA;LB;22;72
Thilo Kehrer;GER;CB;30;78
Mohammed Salisu;GHA;CB;27;77
Eric Dier;ENG;CB;32;77
Christian Mawissa;FRA;CB;21;74
Mamadou Coulibaly;SEN;CM;22;72
Krépin Diatta;SEN;RW;27;76
Mika Biereth;DEN;ST;23;77
George Ilenikhena;FRA;ST;19;72
""",
"fra-olympique-lyon": """
Dominik Greif;SVK;GK;29;76
Rémy Descamps;FRA;GK;30;70
Ainsley Maitland-Niles;ENG;RB;29;75
Hans Hateboer;NED;RB;32;72
Abner Vinícius;BRA;LB;26;76
Nicolás Tagliafico;ARG;LB;34;77
Moussa Niakhaté;SEN;CB;30;79
Clinton Mata;ANG;CB;33;76
Ruben Kluivert;NED;CB;25;74
Tanner Tessmann;USA;CDM;25;77
Orel Mangala;BEL;CM;28;76
Pavel Šulc;CZE;CAM;25;78
Adam Karabec;CZE;CAM;23;76
Ernest Nuamah;GHA;RW;22;76
Afonso Moreira;POR;LW;21;74
Martín Satriano;URU;ST;25;75
""",
"fra-stade-rennais-fc": """
Brice Samba;FRA;GK;32;80
Mathys Silistrie;FRA;GK;22;68
Przemysław Frankowski;POL;RB;31;76
Alidu Seidu;GHA;RB;26;75
Quentin Merlin;FRA;LB;24;76
Lilian Brassier;FRA;CB;27;76
Jérémy Jacquet;FRA;CB;21;75
Anthony Rouault;FRA;CB;25;76
Abdelhamid Aït Boudlal;MAR;CB;20;72
Valentin Rongier;FRA;CM;31;78
Seko Fofana;CIV;CM;31;78
Mahdi Camara;FRA;CM;28;76
Djaoui Cissé;FRA;CM;22;76
Ludovic Blas;FRA;CAM;28;77
Arnaud Nordin;FRA;LW;28;75
Breel Embolo;SUI;ST;29;77
Mohamed Kader Meïté;FRA;ST;19;72
""",
"fra-losc-lille": """
Thomas Meunier;BEL;RB;35;75
Tiago Santos;POR;RB;24;76
Romain Perraud;FRA;LB;29;76
Alexsandro Ribeiro;BRA;CB;27;78
Nathan Ngoy;BEL;CB;23;75
Aïssa Mandi;ALG;CB;35;74
Benjamin André;FRA;CDM;36;76
Nabil Bentaleb;ALG;CM;31;75
Ngal'ayel Mukau;BEL;CM;21;74
Ethan Mbappé;FRA;CM;19;73
Osame Sahraoui;NOR;LW;25;77
Félix Correia;POR;LW;25;75
Matías Fernández-Pardo;BEL;RW;21;76
Hamza Igamane;MAR;ST;23;77
""",
"fra-olympique-marseille": """
Jeffrey de Lange;NED;GK;28;68
Amir Murillo;PAN;RB;30;73
Facundo Medina;ARG;LB;27;76
Emerson Palmieri;ITA;LB;32;74
Nayef Aguerd;MAR;CB;30;77
CJ Egan-Riley;ENG;CB;23;74
Geoffrey Kondogbia;CTA;CDM;33;75
Angel Gomes;ENG;CM;25;76
Bilal Nadir;FRA;CM;22;72
Matt O'Riley;DEN;CAM;25;77
Igor Paixão;BRA;LW;26;77
Timothy Weah;USA;RW;26;75
Neal Maupay;FRA;ST;30;72
""",
"fra-rc-lens": """
Ruben Aguilar;FRA;RB;32;75
Matthieu Udol;FRA;LB;30;74
Deiver Machado;COL;LB;32;74
Jonathan Gradit;FRA;CB;33;75
Malang Sarr;FRA;CB;27;76
Samson Baidoo;AUT;CB;21;75
Ismaëlo Ganiou;FRA;CB;21;73
Juma Bah;SLE;CB;20;72
Mamadou Sangaré;MLI;CM;23;76
Adrien Thomasson;FRA;CM;32;77
Allan Saint-Maximin;FRA;LW;29;77
Abdallah Sima;SEN;LW;25;76
Odsonne Édouard;FRA;ST;28;76
M'Bala Nzola;ANG;ST;30;75
Wesley Saïd;FRA;ST;31;74
Morgan Guilavogui;FRA;ST;28;74
Rémy Labeau Lascary;FRA;ST;23;72
""",
"fra-ogc-nice": """
Yehvann Diouf;FRA;GK;26;76
Jonathan Clauss;FRA;RB;34;77
Ali Abdi;TUN;LB;32;75
Melvin Bard;FRA;LB;25;76
Moïse Bombito;CAN;CB;26;78
Antoine Mendy;FRA;CB;22;75
Youssouf Ndayishimiye;BDI;CB;27;76
Kojo Peprah Oppong;GHA;CB;22;74
Hicham Boudaoui;ALG;CDM;26;77
Charles Vanhoutte;BEL;CM;27;75
Morgan Sanson;FRA;CM;32;75
Tanguy Ndombele;FRA;CM;29;75
Tom Louchet;FRA;CM;22;73
Sofiane Diop;MAR;CAM;26;78
Jérémie Boga;CIV;LW;29;76
Mohamed-Ali Cho;FRA;LW;22;76
Isak Jansson;SWE;RW;24;74
""",
"fra-paris-fc": """
Kevin Trapp;GER;GK;36;76
Obed Nkambadio;FRA;GK;23;72
Samir Chergui;FRA;RB;27;72
Thibault De Smet;BEL;LB;28;74
Nhoa Sangui;FRA;LB;20;71
Otávio;BRA;CB;31;75
Moustapha Mbow;SEN;CB;26;74
Tuomas Ollila;FIN;CB;25;73
Maxime López;FRA;CM;28;76
Pierre Lees-Melou;FRA;CM;33;75
Vincent Marchetti;FRA;CM;29;73
Lohann Doucet;FRA;CM;23;73
Ilan Kebbal;ALG;CAM;28;77
Moses Simon;NGA;LW;31;76
Luca Koleosho;ITA;LW;22;74
Jean-Philippe Krasso;CIV;ST;29;75
Willem Geubbels;FRA;ST;24;74
""",
"fra-rc-strasbourg-alsace": """
Mike Penders;BEL;GK;21;74
Guéla Doué;CIV;RB;24;76
Ben Chilwell;ENG;LB;30;75
Ismaël Doukouré;FRA;CB;23;75
Andrew Omobamidele;IRL;CB;24;74
Abakar Sylla;CIV;CB;23;74
Lucas Høgsberg;DEN;CB;20;72
Mathis Amougou;FRA;CDM;20;73
Félix Lemaréchal;FRA;CM;23;75
Julio Enciso;PAR;CAM;22;76
Diego Moreira;BEL;LW;22;76
Sebastian Nanasi;SWE;LW;24;76
Martial Godo;ENG;LW;23;74
Samuel Amo-Ameyaw;ENG;RW;20;72
Joaquín Panichelli;ARG;ST;23;77
""",
"fra-aj-auxerre": """
Donovan Léon;FRA;GK;33;75
Théo De Percin;FRA;GK;25;70
Marvin Senaya;FRA;RB;25;72
Paul Joly;FRA;RB;26;70
Gideon Mensah;GHA;LB;27;74
Fredrik Oppegård;NOR;LB;23;72
Sinaly Diomandé;CIV;CB;25;74
Clément Akpa;FRA;CB;24;72
Jubal;BRA;CB;32;72
Elisha Owusu;GHA;CDM;28;75
Kévin Danois;FRA;CM;21;73
Lasso Coulibaly;CIV;CM;23;72
Gauthier Hein;FRA;CAM;30;74
Josué Casimir;FRA;RW;25;72
Lassine Sinayoko;MLI;ST;26;75
Danny Namaso;ENG;ST;25;72
""",
"fra-angers-sco": """
Hervé Koffi;BFA;GK;29;74
Carlens Arcus;HAI;RB;29;73
Jacques Ekomié;FRA;LB;22;72
Jordan Lefort;FRA;LB;32;72
Florent Hanin;FRA;LB;35;70
Emmanuel Biumla;FRA;CB;26;70
Lilian Raolisoa;FRA;CB;25;70
Himad Abdelli;ALG;CM;27;76
Haris Belkebla;ALG;CM;32;73
Yassin Belkhdim;FRA;CM;24;73
Farid El Melali;ALG;LW;29;73
Jim Allevinah;GAB;RW;31;72
Sidiki Chérif;FRA;ST;19;74
Prosper Peter;NGA;ST;21;70
""",
"fra-fc-lorient": """
Yvon Mvogo;SUI;GK;32;74
Bingourou Kamara;SEN;GK;29;67
Igor Silva;BRA;RB;29;71
Darlin Yongwa;CMR;LB;25;72
Montassar Talbi;TUN;CB;28;74
Bamo Meïté;CIV;CB;24;72
Formose Mendy;SEN;CB;25;71
Laurent Abergel;FRA;CDM;33;73
Jean-Victor Makengo;FRA;CM;27;73
Arsène Kouassi;FRA;CM;20;71
Théo Le Bris;FRA;RW;23;73
Pablo Pagis;FRA;LW;23;73
Joel Mvuka;NOR;LW;23;71
Tosin Aiyegun;BEN;ST;28;73
Mohamed Bamba;CIV;ST;24;72
""",
"fra-fc-toulouse": """
Guillaume Restes;FRA;GK;21;75
Alex Dominguez;FRA;GK;27;66
Warren Kamanzi;NOR;RB;25;72
Djibril Sidibé;MLI;RB;33;70
Mark McKenzie;USA;CB;27;74
Charlie Cresswell;ENG;CB;23;74
Rasmus Nicolaisen;DEN;CB;29;72
Dayann Methalie;FRA;CB;20;69
Cristian Cásseres Jr.;VEN;CM;26;73
Abu Francis;GHA;CM;25;72
Vincent Sierro;SUI;CM;30;73
Aron Dønnum;NOR;LW;28;73
Santiago Hidalgo;ARG;LW;21;71
Yann Gboho;FRA;RW;25;73
Frank Magri;CMR;ST;26;71
Emersonn;BRA;ST;26;71
""",
"fra-stade-brestois-29": """
Grégoire Coudert;FRA;GK;26;72
Kenny Lala;FRA;RB;35;72
Bradley Locko;FRA;LB;24;74
Daouda Guindo;MLI;LB;23;72
Brendan Chardonnet;FRA;CB;31;74
Soumaïla Coulibaly;FRA;CB;22;74
Julien Le Cardinal;FRA;CB;28;72
Hugo Magnetti;FRA;CM;28;74
Edimilson Fernandes;SUI;CM;30;74
Kamory Doumbia;MLI;CAM;23;75
Romain Faivre;FRA;CAM;28;74
Romain Del Castillo;FRA;RW;30;75
Mathias Pereira Lage;FRA;RW;29;74
Ludovic Ajorque;FRA;ST;32;75
Mama Baldé;GNB;ST;30;72
""",
"fra-le-havre-ac": """
Arthur Desmas;FRA;GK;32;74
Mathieu Gorgelin;FRA;GK;35;68
Loïc Négo;HUN;RB;35;70
Fodé Ballo-Touré;SEN;LB;29;72
Gautier Lloris;FRA;CB;31;72
Arouna Sangante;SEN;CB;24;73
Etienne Youte Kinkoue;FRA;CB;24;72
Yoann Salmier;FRA;CB;33;70
Abdoulaye Touré;GUI;CM;32;73
Yassine Kechta;MAR;CM;24;74
Rassoul Ndiaye;SEN;CM;24;73
Simon Ebonog;CMR;CM;21;72
André Ayew;GHA;RW;36;72
Issa Soumaré;SEN;ST;25;73
""",
"fra-estac-troyes": """
Abdu Conté;POR;LB;27;70
Ismaël Boura;FRA;LB;25;70
Martin Adeline;FRA;CM;22;70
Rafiki Saïd;COM;LW;25;70
Renaud Ripart;FRA;ST;32;70
""",
}

def potential(age, ovr):
    """Вилка потенциала по возрасту: молодым - рост, с 24 лет - нынешний уровень."""
    if age >= 24:
        return ovr, ovr
    grow = 24 - age
    return min(95, ovr + round(grow * 1.3)), min(97, ovr + round(grow * 2.4))

def main():
    rows = list(csv.DictReader(open(CSV, encoding="utf-8")))
    fields = list(rows[0].keys())
    have = {r["name"]: r["club"] for r in rows}
    db = sqlite3.connect(ROOT / "data" / "football.db")
    clubs = {r[0] for r in db.execute("SELECT club_id FROM clubs")}
    nats = {r[0] for r in db.execute("SELECT fifa_code FROM countries")}
    added, skipped, bad, clash = 0, 0, [], []
    for club, text in SQUADS.items():
        if club not in clubs:
            bad.append(("club", club)); continue
        for line in text.strip().splitlines():
            name, nat, pos, age, ovr = [x.strip() for x in line.split(";")]
            if nat not in nats:
                bad.append(("nat", line)); continue
            if name in have:
                skipped += 1
                if have[name] != club:                    # тёзка в другом клубе: нужно другое написание имени
                    clash.append(f"{name}: {have[name]} / {club}")
                continue
            lo, hi = potential(int(age), int(ovr))
            rows.append({"tier": "notable", "name": name, "nat": nat, "pos": pos, "age": age, "ovr": ovr,
                         "pot_lo": str(lo), "pot_hi": str(hi), "club": club})
            have[name] = club; added += 1
    if bad:
        sys.exit(f"ошибки: {bad}")
    with open(CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader(); w.writerows(rows)
    print(f"добавлено {added}, уже были {skipped}, всего игроков {len(rows)}")
    if clash:
        print("тёзки в разных клубах (не добавлены, нужно другое написание):", "; ".join(clash))

if __name__ == "__main__":
    main()
