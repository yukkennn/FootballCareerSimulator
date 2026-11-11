"""Имена и фамилии для сгенерированных людей (игроки, тренеры, скауты) - по региону страны.

gen_name(rng, nat, conf): страна -> регион (REGION), если страны нет в списке - регион конфедерации (CONF_REGION).
В некоторых регионах бывают двойные фамилии (Испания, Латинская Америка, Португалия, Бразилия) - это тоже вариация.
"""

def _w(s):
    return s.split()

def _l(s):
    return [x.strip() for x in s.split(",") if x.strip()]

NAMES = {
    "es": (_w("Alejandro Pablo Diego Javier Sergio Mateo Hugo Álvaro Iker Marcos Adrián Rodrigo Daniel David Carlos Raúl Rubén Óscar "
              "Jorge Íñigo Unai Aitor Asier Gorka Ander Mikel Jon Pau Marc Arnau Pol Gerard Oriol Eric Aleix Borja Dani Nacho Fran "
              "Alberto Víctor Samuel Izan Gonzalo Martín Manuel Antonio Miguel Ángel Jesús Joel Rafa"),
           _l("García, Fernández, Rodríguez, López, Martínez, Sánchez, Pérez, Gómez, Martín, Jiménez, Ruiz, Hernández, Díaz, Moreno, "
              "Muñoz, Álvarez, Romero, Alonso, Gutiérrez, Navarro, Torres, Domínguez, Vázquez, Ramos, Gil, Ramírez, Serrano, Blanco, "
              "Molina, Morales, Suárez, Ortega, Delgado, Castro, Ortiz, Rubio, Marín, Sanz, Iglesias, Núñez, Medina, Garrido, Cortés, "
              "Castillo, Santos, Lozano, Guerrero, Cano, Prieto, Méndez, Cruz, Calvo, Gallego, Herrera, Márquez, León, Peña, Cabrera, "
              "Aguirre, Etxeberria, Zubizarreta, Arrieta, Goikoetxea, Puig, Vidal, Ferrer, Soler, Roca, Pujol, Vila, Bosch")),
    "la": (_w("Mateo Santiago Thiago Emiliano Facundo Valentín Joaquín Agustín Franco Lautaro Tomás Benjamín Nicolás Matías Lucas "
              "Gonzalo Bruno Ezequiel Maximiliano Leandro Julián Enzo Alexis Kevin Brayan Jhon Yerson Wilmer Duván Jefferson Anderson "
              "Cristian Luis Juan Andrés Felipe Camilo Sebastián Esteban Germán Rodrigo Gastón Nahuel Thiago Ian Dylan Elías Iván "
              "Rubén Edson Hirving Uriel Alexis Érick Jesús Raúl Orbelín Diego Ángel"),
           _l("González, Rodríguez, Gómez, Fernández, López, Díaz, Martínez, Pérez, Romero, Sosa, Álvarez, Torres, Ruiz, Ramírez, "
              "Flores, Acosta, Benítez, Medina, Herrera, Suárez, Aguirre, Giménez, Gutiérrez, Pereyra, Rojas, Molina, Castro, Ortiz, "
              "Silva, Núñez, Luna, Juárez, Cabrera, Ríos, Morales, Godoy, Domínguez, Vera, Ledesma, Paredes, Correa, Cáceres, Villalba, "
              "Quintero, Cuadrado, Mosquera, Valencia, Arboleda, Caicedo, Hurtado, Palacios, Mina, Borja, Zapata, Montoya, Vargas, "
              "Cardona, Salazar, Arango, Ospina, Mendoza, Guzmán, Chávez, Hernández, Lozano, Corona, Alvarado, Orozco, Vega, Lainez, "
              "Valdez, Espinoza, Figueroa, Bustos, Pizarro, Carrasco, Bravo, Contreras, Fuentes, Araya, Valdivia")),
    "br": (_w("João Pedro Gabriel Rafael Lucas Matheus Vitor Gustavo Thiago Bruno Rodrigo Caio Davi Enzo Murilo Vinícius Felipe "
              "Guilherme Leonardo Eduardo Igor Kaio Kauã Wesley Willian Wendell Douglas Everton Éder Fabinho Danilo Renan Rômulo "
              "Arthur Raphael Endrick Estêvão Yuri Luan Hugo Diego André Fernando Marcos Paulo Ronaldo Alisson Ederson Breno Talles"),
           _l("Silva, Santos, Oliveira, Souza, Costa, Pereira, Almeida, Ferreira, Carvalho, Gomes, Ribeiro, Martins, Rocha, Lima, "
              "Araújo, Mendes, Nunes, Moreira, Barbosa, Teixeira, Cardoso, Batista, Freitas, Dias, Castro, Campos, Andrade, Correia, "
              "Fernandes, Vieira, Monteiro, Moraes, Ramos, Machado, Lopes, Marques, Pinto, Cavalcanti, Nascimento, Rezende, Peixoto, "
              "Fonseca, Siqueira, Brandão, Bezerra, Medeiros, Farias, Xavier, Queiroz, Assis, Paixão, Magalhães, Guimarães, Coutinho")),
    "pt": (_w("João Pedro Rúben Diogo Gonçalo Tiago Rafael Bernardo Francisco Nuno André Rui Duarte Afonso Tomás Martim Rodrigo "
              "Vitinha Fábio Hélder Renato Ricardo Miguel Vasco Henrique Salvador Gil Simão Bruno Nélson Carlos Paulo Jorge Mário"),
           _l("Silva, Santos, Ferreira, Pereira, Oliveira, Costa, Rodrigues, Martins, Jesus, Sousa, Fernandes, Gonçalves, Gomes, "
              "Lopes, Marques, Alves, Almeida, Ribeiro, Pinto, Carvalho, Teixeira, Moreira, Correia, Mendes, Nunes, Soares, Vieira, "
              "Monteiro, Cardoso, Rocha, Neves, Coelho, Cruz, Cunha, Pires, Ramos, Reis, Simões, Antunes, Matos, Fonseca, Morais, "
              "Leite, Tavares, Magalhães, Baptista, Andrade, Quaresma, Palhinha, Semedo")),
    "en": (_w("Jack Harry James Oliver Charlie George Mason Callum Jacob Ethan Kai Leo Alfie Archie Noah Tyler Reece Jayden Liam "
              "Connor Thomas William Joe Ben Sam Lewis Ryan Jordan Aaron Declan Jude Cole Bukayo Marcus Kieran Luke Max Freddie "
              "Rhys Kyle Dean Scott Ross Craig Ellis Morgan Dylan Owen Rory Cian Seán Conor Darragh Finn Toby Rico Jarrod"),
           _l("Smith, Jones, Taylor, Brown, Wilson, Walker, Wright, Clarke, Hughes, Ward, Morgan, Bennett, Hill, Cooper, Mitchell, "
              "Turner, Robinson, Hall, Green, Doherty, Johnson, Williams, Davies, Evans, Thomas, Roberts, Lewis, Jackson, White, "
              "Harris, Martin, Thompson, Wood, Wright, Edwards, Baker, Lee, Allen, King, Scott, Young, Carter, Phillips, Watson, "
              "Murray, Campbell, Stewart, MacDonald, Fraser, Reid, Henderson, Kelly, Murphy, O'Brien, Byrne, Ryan, O'Connor, Walsh, "
              "McCarthy, Gallagher, Doyle, Lynch, Quinn, Barnes, Palmer, Saka, Rice, Foden, Mainoo, Gordon, Jenkins, Price, Lloyd")),
    "us": (_w("Tyler Christian Weston Gio Brenden Josh Zack Miles Jordan Malik Caleb Brandon Cameron Aidan Cade Diego Ricardo "
              "Paxton Jalen DeAndre Darius Isaiah Andrew Matt Chris Mike Kellyn Folarin Haji Tanner Owen Luca Damion Jonathan"),
           _l("Johnson, Williams, Brown, Davis, Miller, Wilson, Anderson, Thomas, Moore, Jackson, Martin, Thompson, White, Harris, "
              "Clark, Lewis, Robinson, Walker, Young, Allen, Wright, Scott, Green, Adams, Baker, Nelson, Hill, Campbell, Mitchell, "
              "Roberts, Carter, Phillips, Evans, Turner, Parker, Collins, Edwards, Stewart, Morris, Murphy, Cook, Rogers, Reyna, "
              "McKennie, Pulisic, Weah, Aaronson, Musah, Richards, Robinson, Ream, Zimmerman, Tillman, Pepi, Sargent, Turner")),
    "fr": (_w("Lucas Hugo Théo Nathan Enzo Mathis Rayan Ilyes Maxime Antoine Adrien Yanis Evan Mathys Kylian Sacha Bradley Malo "
              "Louis Gabriel Jules Arthur Raphaël Léo Tom Noah Baptiste Clément Quentin Florian Romain Benjamin Aurélien Jérémy "
              "Kévin Warren Désiré Eduardo Randal Wesley Jonathan Benoît Alexis Corentin Tanguy Mattéo Lenny Kingsley Rayan"),
           _l("Martin, Bernard, Dubois, Moreau, Laurent, Lefebvre, Girard, Bonnet, Guérin, Lacroix, Faure, Thomas, Petit, Robert, "
              "Richard, Durand, Leroy, Simon, Michel, Garcia, David, Bertrand, Roux, Vincent, Fournier, Morel, Girard, André, Mercier, "
              "Blanc, Boyer, Chevalier, François, Legrand, Gauthier, Perrin, Robin, Clément, Morin, Nicolas, Henry, Roussel, Mathieu, "
              "Fofana, Diallo, Camara, Koné, Traoré, Mendy, Kamara, Sissoko, Mbaye, Konaté, Doucouré, Kanté, Tchouaméni, Zaïre-Emery, "
              "Cherki, Barcola, Olise, Saliba, Upamecano, Koundé, Hernandez, Digne, Clauss, Thuram, Kolo Muani, Lacazette")),
    "de": (_w("Lukas Leon Felix Jonas Maximilian Paul Niklas Tim Jan Florian Moritz Finn Luca Ben Elias Noah Julian Kai Leroy Joshua "
              "Thomas Manuel Marc-André Antonio Robin David Nico Jamal Florian Kevin Dominik Philipp Sebastian Marcel Tobias Fabian "
              "Matthias Christoph Lennart Malick Yann Aleksandar Mats Benedikt Karim Angelo Marvin"),
           _l("Müller, Schmidt, Schneider, Fischer, Weber, Wagner, Becker, Hoffmann, Koch, Richter, Wolf, Neuhaus, Brandt, Schulz, "
              "Krämer, Lehmann, Meyer, Schäfer, Bauer, Klein, Schröder, Neumann, Schwarz, Zimmermann, Braun, Hofmann, Hartmann, Lange, "
              "Schmitt, Werner, Krause, Meier, Schmid, Schulze, Maier, Köhler, Herrmann, König, Walter, Mayer, Huber, Kaiser, Fuchs, "
              "Peters, Lang, Scholz, Möller, Weiß, Jung, Hahn, Vogel, Friedrich, Keller, Günther, Frank, Berger, Winkler, Roth, Beck, "
              "Lorenz, Baumann, Franke, Albrecht, Ludwig, Gnabry, Musiala, Wirtz, Havertz, Kimmich, Goretzka, Rüdiger, Tah, Sané")),
    "it": (_w("Lorenzo Matteo Alessandro Andrea Francesco Federico Davide Riccardo Giacomo Nicolò Samuele Tommaso Gabriele Pietro "
              "Leonardo Marco Luca Simone Stefano Giorgio Daniele Gianluigi Alessio Manuel Mattia Edoardo Filippo Christian Emanuele "
              "Fabio Giovanni Antonio Salvatore Vincenzo Domenico Raffaele Sandro Bryan Destiny Moise"),
           _l("Rossi, Russo, Ferrari, Esposito, Bianchi, Romano, Colombo, Ricci, Marino, Greco, Bruno, Gallo, Conti, De Luca, Mancini, "
              "Lombardi, Costa, Giordano, Rizzo, Moretti, Barbieri, Fontana, Santoro, Mariani, Rinaldi, Caruso, Ferrara, Galli, "
              "Martini, Leone, Longo, Gentile, Martinelli, Vitale, Serra, Coppola, De Santis, D'Angelo, Marchetti, Parisi, Villa, "
              "Conte, Ferraro, Ferri, Fabbri, Bianco, Marini, Grasso, Valentini, Messina, Sala, De Rosa, Gatti, Pellegrini, Palumbo, "
              "Sanna, Farina, Rizzi, Monti, Cattaneo, Morelli, Amato, Silvestri, Mazza, Testa, Barella, Bastoni, Dimarco, Frattesi")),
    "nl": (_w("Daan Sem Jesse Thijs Milan Lars Ruben Bram Luuk Xavi Jorrel Noa Finn Levi Bas Joris Jurriën Ryan Teun Stijn Wout "
              "Kenneth Quinten Micky Cody Denzel Brian Justin Mats Arne Lander Jarne Seppe Wout Thibaut Romelu Youri Amadou Leandro"),
           _l("de Jong, Jansen, de Vries, van Dijk, Bakker, Visser, Smit, Meijer, Mulder, Peeters, Janssens, Maes, van den Berg, "
              "van der Berg, Bos, Vos, Peters, Hendriks, van Leeuwen, Dekker, Brouwer, de Wit, Dijkstra, Smits, de Graaf, van der Meer, "
              "van der Linden, Kok, Jacobs, de Haan, Vermeulen, van den Heuvel, van der Veen, van Beek, de Bruijn, de Boer, Willems, "
              "Claes, Goossens, Wouters, De Smet, Mertens, Dubois, Lambert, Vermeersch, Timber, Gravenberch, Frimpong, Simons, Malen")),
    "yu": (_w("Luka Marko Nikola Filip Petar Stefan Ivan Josip Mateo Lovro Dominik Mario Ante Duje Bruno Domagoj Dejan Dušan Aleksandar "
              "Miloš Sergej Strahinja Lazar Vanja Nemanja Uroš Andrija Edin Haris Amar Ermin Kenan Jasmin Benjamin Žan Jan Timi "
              "Benjamin Adam Jure Stevan Darko Goran Vedran Igor Elif Eljif Bojan Enis"),
           _l("Horvat, Kovačević, Babić, Marić, Jurić, Novak, Kovač, Knežević, Vuković, Marković, Petrović, Matić, Tomić, Pavlović, "
              "Jovanović, Nikolić, Ilić, Đorđević, Stojanović, Popović, Živković, Mitrović, Milinković, Vlahović, Tadić, Lukić, Gudelj, "
              "Modrić, Perišić, Brozović, Kramarić, Gvardiol, Šutalo, Sučić, Baturina, Majer, Vlašić, Pašalić, Livaja, Budimir, Džeko, "
              "Pjanić, Kolašinac, Hadžikadunić, Begović, Šeško, Oblak, Ilićić, Elsnik, Gnezda, Šporar, Mlakar, Bardhi, Elmas, Alioski, "
              "Jovetić, Savić, Vujačić, Krstović")),
    "ru": (_w("Ivan Artem Kirill Dmitry Alexei Sergei Maxim Nikita Daniil Egor Matvei Andrei Pavel Igor Roman Anton Denis Ilya Fyodor "
              "Arsen Aleksandr Mikhail Vladislav Vyacheslav Konstantin Stanislav Yaroslav Gleb Timofei Bogdan Ruslan Vadim"),
           _l("Ivanov, Smirnov, Kuznetsov, Popov, Vasiliev, Petrov, Sokolov, Mikhailov, Novikov, Fyodorov, Morozov, Volkov, Alekseev, "
              "Lebedev, Semenov, Egorov, Pavlov, Kozlov, Stepanov, Nikolaev, Orlov, Andreev, Makarov, Nikitin, Zakharov, Zaitsev, "
              "Solovyov, Borisov, Yakovlev, Grigoriev, Romanov, Vorobyov, Sergeev, Kuzmin, Frolov, Alexandrov, Dmitriev, Korolev, "
              "Gusev, Kiselyov, Ilyin, Maksimov, Polyakov, Sorokin, Vinogradov, Kovalev, Belov, Medvedev, Antonov, Tarasov, Zhukov, "
              "Golovin, Batrakov, Glushenkov, Barinov, Safonov, Sobolev, Miranchuk, Chalov, Dzyuba, Zhirkov, Kudryashov")),
    "ua": (_w("Andriy Oleksandr Mykola Bohdan Vitaliy Taras Yaroslav Ruslan Artem Mykhailo Illia Heorhiy Danylo Vladyslav Ivan "
              "Serhiy Roman Viktor Oleh Yevhen Maksym Dmytro Anatoliy Valeriy"),
           _l("Kovalenko, Bondarenko, Shevchenko, Tkachenko, Kravchenko, Boyko, Melnyk, Oliynyk, Shevchuk, Polishchuk, Lysenko, "
              "Marchenko, Moroz, Savchenko, Rudenko, Pavlenko, Klymenko, Kovalchuk, Zinchenko, Mudryk, Tsyhankov, Yarmolenko, "
              "Malinovskyi, Sudakov, Dovbyk, Trubin, Lunin, Zabarnyi, Mykolenko, Matviyenko, Stepanenko, Yaremchuk, Vanat, Bondar, "
              "Brazhko, Shaparenko, Sydorchuk, Konoplyanka, Rakitskiy, Karavaev")),
    "pl": (_w("Jakub Kacper Mateusz Bartosz Michał Piotr Krzysztof Kamil Szymon Wojciech Łukasz Tomasz Adam Dawid Przemysław "
              "Sebastian Patryk Damian Filip Oskar Nicola Robert Grzegorz Marcin Paweł Arkadiusz Karol Bartłomiej Maciej Jan"),
           _l("Nowak, Kowalski, Wiśniewski, Wójcik, Kowalczyk, Kamiński, Lewandowski, Zieliński, Szymański, Woźniak, Dąbrowski, "
              "Kozłowski, Jankowski, Mazur, Kwiatkowski, Krawczyk, Piotrowski, Grabowski, Nowakowski, Pawłowski, Michalski, "
              "Nowicki, Adamczyk, Dudek, Zając, Wieczorek, Jabłoński, Król, Majewski, Olszewski, Jaworski, Wróbel, Malinowski, "
              "Pawlak, Witkowski, Walczak, Stępień, Górski, Rutkowski, Michalak, Sikora, Ostrowski, Baran, Duda, Szewczyk, Tomaszewski, "
              "Szczęsny, Bednarek, Kiwior, Cash, Moder, Świderski, Piątek, Frankowski, Skóraś, Urbański, Kamiński, Zalewski")),
    "cz": (_w("Jakub Tomáš Lukáš Ondřej Adam Matěj Vojtěch Jan Patrik Michal Pavel Martin David Filip Antonín Václav Ladislav "
              "Marek Juraj Milan Stanislav Peter Róbert Dávid Ivan Miroslav Tomas Dominik Ľubomír Norbert"),
           _l("Novák, Svoboda, Novotný, Dvořák, Černý, Procházka, Kučera, Veselý, Horák, Němec, Pokorný, Marek, Pospíšil, Hájek, "
              "Jelínek, Král, Růžička, Beneš, Fiala, Sedláček, Doležal, Zeman, Kolář, Navrátil, Čermák, Vaněk, Urban, Blažek, "
              "Souček, Schick, Coufal, Holeš, Kuchta, Hložek, Provod, Krejčí, Barák, Šulc, Chorý, Sadílek, Jurásek, Staněk, "
              "Horváth, Kováč, Varga, Tóth, Nagy, Baláž, Szabó, Molnár, Lobotka, Škriniar, Hancko, Duda, Haraslín, Bero, Strelec")),
    "ro": (_w("Andrei Alexandru Ionuț Răzvan Florin Nicolae Bogdan Dennis Radu Vlad Mihai Cristian Gheorghe Adrian Valentin Darius "
              "Denis Alexandru Ianis Marius Ciprian Claudiu Ștefan Octavian Constantin Dorin Vadim Artur Ion Sergiu"),
           _l("Popescu, Ionescu, Popa, Pop, Radu, Dumitru, Stan, Stoica, Gheorghe, Rusu, Munteanu, Matei, Constantin, Șerban, Moldovan, "
              "Lungu, Marin, Mihai, Ciobanu, Toma, Dinu, Barbu, Florea, Ene, Neagu, Nistor, Ilie, Tănase, Lazăr, Moraru, Diaconu, "
              "Răduță, Drăguș, Stanciu, Hagi, Man, Mihăilă, Burcă, Rațiu, Mogoș, Marin, Nedelcearu, Coman, Pușcaș, Ivan, Bîrligea")),
    "hu": (_w("Dominik Roland Ádám Bence Dániel Márton Zsolt Attila Péter Balázs Milos Kristóf Barnabás András Gergő Levente "
              "Bendegúz Tamás Krisztián Willi Loïc Zoltán Norbert Csaba Endre"),
           _l("Nagy, Kovács, Tóth, Szabó, Horváth, Varga, Kiss, Molnár, Németh, Farkas, Balogh, Papp, Takács, Juhász, Lakatos, "
              "Mészáros, Oláh, Simon, Rácz, Fekete, Szilágyi, Török, Fehér, Balázs, Gál, Kocsis, Szoboszlai, Sallai, Kerkez, "
              "Schäfer, Gazdag, Nego, Fiola, Orbán, Botka, Styles, Ádám, Varga, Dibusz, Gulácsi")),
    "bg": (_w("Georgi Ivan Dimitar Nikolay Martin Kiril Stanislav Valentin Todor Aleksandar Petar Radoslav Ilian Atanas Hristo "
              "Yordan Svetoslav Spas Borislav Tsvetan"),
           _l("Ivanov, Georgiev, Dimitrov, Petrov, Nikolov, Hristov, Stoyanov, Todorov, Iliev, Atanasov, Petkov, Angelov, Vasilev, "
              "Kolev, Popov, Marinov, Yordanov, Mihaylov, Kostov, Stefanov, Despodov, Chochev, Kraev, Minchev, Antov, Cicinho, "
              "Delev, Iliev, Mladenov, Tsvetkov")),
    "ba": (_w("Artūras Lukas Mantas Edvinas Gvidas Justas Paulius Domantas Kristaps Roberts Raivis Jānis Dāvis Mārtiņš Edgars "
              "Karl Mattias Rauno Henri Markus Kristjan Ragnar Siim Tanel Joonas"),
           _l("Kazlauskas, Petrauskas, Jankauskas, Stankevičius, Vasiliauskas, Žukauskas, Butkus, Paulauskas, Urbonas, Navickas, "
              "Gineitis, Girdvainis, Utkus, Bērziņš, Kalniņš, Ozoliņš, Jansons, Ozols, Liepiņš, Krūmiņš, Zariņš, Savaļnieks, Ikaunieks, "
              "Tamm, Saar, Sepp, Mägi, Kask, Kukk, Rebane, Ilves, Pärn, Koppel, Sappinen, Vassiljev, Kait, Puri")),
    "cau": (_w("Giorgi Levan Davit Otar Saba Khvicha Luka Zuriko Guram Lasha Nika Irakli Budu Georges Henrikh Eduard Tigran "
               "Vahan Artak Lucas Kamo Nair Grant Narek"),
            _l("Beridze, Kapanadze, Gelashvili, Maisuradze, Lomidze, Mamardashvili, Kvaratskhelia, Mikautadze, Chakvetadze, Kochorashvili, "
               "Zivzivadze, Kvekveskiri, Davitashvili, Lobjanidze, Kashia, Kiteishvili, Tsitaishvili, Shengelia, Gvilia, Dvali, "
               "Mkhitaryan, Hovhannisyan, Grigoryan, Harutyunyan, Sargsyan, Petrosyan, Ghazaryan, Barseghyan, Bichakhchyan, Spertsyan, "
               "Tiknizyan, Dashyan, Ranos, Hambardzumyan, Adamyan")),
    "al": (_w("Armando Arlind Elseid Kristjan Nedim Taulant Ermir Berat Myrto Jasir Arber Vedat Edon Milot Amir Florent Leart "
              "Lirim Albion Valon Granit Xherdan Muhamed Bersant"),
           _l("Hoxha, Shehu, Gashi, Berisha, Krasniqi, Kelmendi, Morina, Shala, Bytyqi, Hasani, Rexhepi, Hysaj, Ismajli, Djimsiti, "
              "Asllani, Bajrami, Uzuni, Broja, Manaj, Ramadani, Laçi, Seferi, Daku, Muriqi, Rrahmani, Zhegrova, Hadergjonaj, "
              "Vojvoda, Aliti, Muslija, Dresevic, Hodza, Xhaka, Shaqiri")),
    "sc": (_w("Erik Oscar William Elias Mathias Jonas Emil Kasper Viktor Magnus Sander Lucas Alexander Kristoffer Andreas Fredrik "
              "Martin Ole Henrik Joakim Rasmus Mikkel Christian Jesper Simon Jens Gustav Anton Hugo Isak Dejan Jóhann Gylfi Aron "
              "Hákon Ísak Teemu Joel Lukas Glen Jere Riku Brynjar Patrik Albert Morten Jørgen Tobias"),
           _l("Hansen, Johansson, Andersen, Larsen, Nielsen, Karlsson, Berg, Lindqvist, Eriksen, Olsen, Holm, Dahl, Jensen, Pedersen, "
              "Kristiansen, Johannessen, Andersson, Nilsson, Eriksson, Larsson, Olsson, Persson, Svensson, Gustafsson, Pettersson, "
              "Jonsson, Lindberg, Lindström, Bergström, Lundgren, Ødegaard, Sørloth, Nusa, Bobb, Berge, Thorsby, Haaland, Strand, "
              "Højbjerg, Hjulmand, Damsgaard, Højlund, Christensen, Rasmussen, Poulsen, Skov, Mæhle, Kristensen, Gudmundsson, "
              "Sigurdsson, Jónsson, Thorvaldsson, Gunnarsson, Halldórsson, Pukki, Hradecky, Lod, Kamara, Pohjanpalo, Hyvärinen")),
    "gr": (_w("Giorgos Dimitris Konstantinos Christos Nikos Vangelis Kostas Panagiotis Anastasios Thanasis Vasilis Fotis Sotiris "
              "Tasos Andreas Manolis Stelios Lazaros Kyriakos Petros Pieros Charalambos Nikolas Marinos"),
           _l("Papadopoulos, Georgiou, Nikolaidis, Konstantinidis, Pavlidis, Tzolis, Papadakis, Vlachos, Oikonomou, Makris, Karagiannis, "
              "Ioannidis, Papageorgiou, Athanasiou, Christodoulou, Dimitriou, Antoniou, Papanikolaou, Michailidis, Mavropanos, "
              "Tsimikas, Bakasetas, Masouras, Siopis, Kourbelis, Mantalos, Douvikas, Giakoumakis, Fountas, Pelkas, Hatzidiakos, "
              "Kotsiras, Chatzigiovanis, Loizou, Pittas, Charalambous, Kastanos, Sotiriou, Papoulis")),
    "tr": (_w("Arda Kerem Kenan Hakan Orkun Ferdi Barış Emre Cengiz Yusuf Semih Can Mert Oğuz Burak Ozan Abdülkerim Merih Zeki "
              "Kaan Salih İrfan Cenk Altay Uğurcan Okay Eren Ahmet Mehmet Mustafa Berkan İsmail Samet Efecan Bertuğ Yunus Ali"),
           _l("Yılmaz, Kaya, Demir, Şahin, Çelik, Aydın, Öztürk, Arslan, Güler, Yıldız, Kökçü, Akgün, Doğan, Kılıç, Aslan, Çetin, "
              "Kara, Koç, Kurt, Özdemir, Polat, Özkan, Şimşek, Korkmaz, Erdoğan, Aktürkoğlu, Kahveci, Çalhanoğlu, Ünder, Kabak, "
              "Bardakcı, Ayhan, Müldür, Elmalı, Kadıoğlu, Akaydin, Özcan, Yazıcı, Tosun, Ünal, Bayındır, Çakır, Yokuşlu, Kahraman")),
    "ar": (_w("Youssef Achraf Hakim Mohamed Riyad Ismael Amine Omar Karim Bilal Ilias Nayef Sofiane Azzedine Abdessamad Brahim "
              "Ayoub Soufiane Hamza Yassine Zakaria Anass Oussama Mehdi Walid Abde Chadi Saïd Rafik Ramy Youcef Houssem Aïssa "
              "Ellyes Hannibal Wahbi Montassar Elias Taha Adam Ibrahim Rayan Islam Nabil Fares"),
           _l("Benali, Bensaïd, Haddad, El Amrani, Mansouri, Brahimi, Ounahi, Aboukhlal, Ziani, Belkacem, Bennacer, Mahrez, Slimani, "
              "Bensebaini, Aouar, Amoura, Gouiri, Chaïbi, Zerrouki, Atal, Mandi, Benrahma, Belaïli, Bounou, Hakimi, Mazraoui, "
              "Saïss, Amrabat, Ziyech, En-Nesyri, Ezzalzouli, Saibari, El Khannouss, Akhomach, Diaz, Rahimi, Amallah, Khazri, "
              "Msakni, Skhiri, Laïdouni, Talbi, Meriah, Hannachi, Ben Romdhane, Abdi, Mejbri, Achouri, Dahmen, Ben Slimane, Jaziri, "
              "El Idrissi, Alaoui, Bouzidi, Cherkaoui, Tazi, Lahlou, Belhadj, Boudiaf, Hamdi, Trabelsi, Jebali, Gharbi, Haddadi")),
    "gulf": (_w("Mohammed Abdullah Salem Fahad Saud Nasser Faisal Sultan Khalid Ali Hassan Hussein Ahmed Omar Abdulrahman Yasser "
                "Firas Saleh Mohannad Musab Ayman Feras Turki Nawaf Hattan Abdulelah Akram Almoez Bassam Yazan Mousa Ammar "
                "Mahmoud Mostafa Trezeguet Emam Marwan Zizo Ibrahim Karim Ramadan Tarek Hamdi Amr"),
             _l("Al-Dawsari, Al-Shehri, Al-Faraj, Al-Buraikan, Al-Ghannam, Al-Bulaihi, Al-Malki, Al-Owais, Al-Amri, Al-Tambakti, "
                "Kanno, Al-Hamdan, Al-Najei, Al-Aboud, Asiri, Al-Harbi, Al-Qahtani, Al-Mutairi, Al-Otaibi, Al-Zahrani, Afif, "
                "Al-Haydos, Ali, Hatem, Boudiaf, Al-Rawi, Khoukhi, Ahmed, Abdulrahman, Mabkhout, Al-Hammadi, Salmeen, Hussein, "
                "Bayesh, Al-Tamari, Al-Naimat, Olwan, Al-Rashdan, Mahmoud, Al-Somah, Al-Mawas, Harbi, Salah, Marmoush, Elneny, "
                "Hegazi, Fathi, Abdelmonem, Ashour, Zizo, Hamdi, Shobeir, Shenawy, Attia, Salem, Mohsen, Gaber, Tawfik")),
    "ir": (_w("Mehdi Sardar Alireza Saman Ali Ehsan Milad Omid Morteza Hossein Saeid Mohammad Reza Amir Majid Ramin Aria Shoja Roozbeh"),
           _l("Taremi, Azmoun, Jahanbakhsh, Ghoddos, Hosseini, Mohammadi, Ezatolahi, Pouraliganji, Rezaei, Moharrami, Beiranvand, "
              "Kanaani, Nourollahi, Gholizadeh, Karimi, Ahmadi, Rahimi, Jafari, Hashemi, Sadeghi, Mousavi, Shahbazi, Asadi, Torabi")),
    "fa": (_w("Moussa Ibrahima Mamadou Ousmane Abdoulaye Cheikh Amadou Lamine Pape Sadio Ismaïla Idrissa Boulaye Habib Krépin "
              "Nicolas Seko Franck Serge Wilfried Simon Odilon Evann Ibrahim Yves Bertrand Vincent André-Frank Bryan Karl Jean "
              "Fodé Naby Serhou Mohamed Sékou Mahamadou Boubacar Kalidou Nampalys Iliman Nicolas Pierre-Emerick Denis Aaron Jordan"),
           _l("Diop, Sarr, Ndiaye, Gueye, Cissé, Diallo, Touré, Traoré, Koné, Coulibaly, Diarra, Konaté, Keita, Camara, Sow, Fall, "
              "Faye, Mané, Mendy, Koulibaly, Jackson, Diatta, Ndoye, Diao, Seck, Mbaye, Kouyaté, Bamba, Haidara, Doumbia, Sangaré, "
              "Fofana, Kessié, Seri, Kossounou, Ndicka, Boga, Adingra, Pépé, Zaha, Haller, Gradel, Diakité, Onana, Anguissa, "
              "Mbeumo, Aboubakar, Choupo-Moting, Toko Ekambi, Ngamaleu, Castelletto, Wooh, Aubameyang, Lemina, Bouanga, Ecuele Manga, "
              "Guirassy, Kanté, Doucouré, Bissouma, Dembélé, Samassékou, Djiku, Tapsoba, Bertrand, Dayo, Kaboré, Sangaré, Mounié")),
    "af": (_w("Victor Samuel Emmanuel Moses Ibrahim Kelechi Yaw Kwame Ademola Ola Wilfred Alex Calvin Chidera Terem Akor "
              "Samuel Joe Frank Bright Kofi Kwadwo Mohammed Antoine Inaki Thomas Jordan André Abdul Osman Kamaldeen Tariq Ernest "
              "Fisayo Tolu Chukwuemeka Chidozie Uche Ikechukwu Nnamdi Taiwo Kehinde Babajide Sunday Dennis Felix"),
           _l("Osei, Mensah, Boateng, Okafor, Adeyemi, Asante, Eze, Okonkwo, Osimhen, Lookman, Iwobi, Ndidi, Chukwueze, Simon, "
              "Ajayi, Bassey, Aina, Awoniyi, Onuachu, Iheanacho, Ekong, Troost-Ekong, Nwankwo, Okoye, Uzoho, Moffi, Boniface, "
              "Arokodare, Onyeka, Ogbu, Partey, Kudus, Ayew, Williams, Semenyo, Fatawu, Salisu, Djiku, Lamptey, Ashimeru, Sulemana, "
              "Bonsu, Owusu, Appiah, Agyemang, Danso, Amartey, Nuamah, Afriyie, Opoku, Adjei, Quaye, Annan, Tetteh, Ofori, Amankwah")),
    "afe": (_w("Percy Thembinkosi Teboho Ronwen Lyle Aubrey Khuliso Relebohile Siyabonga Bongani Themba Sipho Lebo Michael "
               "Patson Fashion Lameck Enock Kennedy Clatous Stopila Mbwana Simon Novatus Feisal Faustino Kibu Marvelous Tino "
               "Knowledge Jordan Divine Ovidy Emmanuel Jamal Allan Victor Joseph Gift"),
            _l("Tau, Lorch, Mokoena, Williams, Foster, Modiba, Mudau, Mofokeng, Ngezana, Zungu, Mthethwa, Ndlovu, Dlamini, Khumalo, "
               "Nkosi, Mahlangu, Shabalala, Sithole, Daka, Banda, Phiri, Mwila, Musonda, Chama, Sakala, Samatta, Msuva, Mzize, "
               "Dickson, Bocco, Kapombe, Wanyama, Olunga, Omondi, Otieno, Odhiambo, Ochieng, Mugisha, Onyango, Kizito, Okello, "
               "Musona, Nakamba, Billiat, Munetsi, Mahachi, Karuru, Dube, Moyo, Ncube, Chipezeze")),
    "jp": (_w("Takumi Kaoru Ritsu Daichi Takefusa Yuto Kota Hiroki Ao Sota Wataru Junya Daizen Ayase Kyogo Reo Keito Shuto "
              "Takehiro Ko Yukinari Zion Kaishu Hidemasa Shogo Yuki Kento Riku Haruto Sora Ren Yuma Tsubasa Shunsuke Hayato"),
           _l("Tanaka, Suzuki, Takahashi, Watanabe, Ito, Yamamoto, Nakamura, Kubo, Mitoma, Endo, Kobayashi, Kato, Yoshida, Yamada, "
              "Sasaki, Yamaguchi, Matsumoto, Inoue, Kimura, Hayashi, Shimizu, Yamazaki, Mori, Abe, Ikeda, Hashimoto, Ishikawa, "
              "Minamino, Doan, Maeda, Ueda, Furuhashi, Morita, Itakura, Tomiyasu, Machida, Sugawara, Suzuki, Hatate, Sano, Nakamura")),
    "kr": (_w("Min-jae Heung-min Kang-in Jae-sung Hyun-woo Seung-ho Jun-ho Ji-sung Woo-yeong In-beom Gue-sung Hee-chan Young-woo "
              "Seol Tae-hwan Jin-su Seung-gyu Yang-min Hyeon-gyu Ji-soo Dong-jun Sang-ho Chang-hoon Jin-seob"),
           _l("Kim, Lee, Park, Choi, Son, Hwang, Jung, Yang, Kang, Cho, Yoon, Jang, Lim, Han, Oh, Seo, Shin, Kwon, Song, Jeon, "
              "Hong, Ko, Moon, Bae, Baek")),
    "cn": (_w("Wei Lei Hao Jun Tao Yang Chen Bo Wu Xi Zhi Jie Yu Long Peng Fei Yi Kai Rui Ming Hui Shuai Bin Qiang Xiang"),
           _l("Wang, Li, Zhang, Liu, Chen, Wu, Zhao, Huang, Zhou, Xu, Sun, Ma, Zhu, Hu, Guo, He, Lin, Gao, Luo, Zheng, Liang, "
              "Xie, Song, Tang, Han, Feng, Deng, Cao, Peng, Zeng, Xiao, Tian, Dong, Pan, Yuan, Cai, Jiang, Yu, Du, Ye, Cheng")),
    "sea": (_w("Supachok Chanathip Theerathon Ekanit Suphanat Quang Hai Van Hau Tien Linh Marselino Pratama Witan "
               "Egy Asnawi Safawi Arif Akhyar Faisal Luqman Jordan Rizky Teerasil Sarach Elkan Thom Jay Ivar Rafael Justin"),
            _l("Sarachat, Songkrasin, Bunmathan, Chaided, Mueanta, Nguyen, Tran, Le, Pham, Hoang, Vu, Do, Bui, Dang, Ferdinan, "
               "Arhan, Sulaeman, Maulana, Mangkualam, Struick, Idzes, Hubner, Pelupessy, Rasid, Halim, Rashid, Morales, Haddad, "
               "Dolah, Aziz, Ramli, Dewa, Saputra, Wijaya, Santoso, Hidayat, Siregar, Situmorang, Kusuma")),
    "ca": (_w("Alisher Bauyrzhan Islam Ramazan Askhat Dastan Nurlan Arsen Timur Daniyar Abbos Eldor Otabek Jaloliddin Abdukodir "
              "Khusniddin Oston Azizbek Eldor Jamshid Rustam Maksim Mahir Emin Ramil Bahlul Toral Renat Kanat Erlan Beknaz"),
           _l("Zhaksylykov, Seydakhmet, Tagybergen, Kenzhebek, Ismailov, Abiken, Orazov, Fayzullaev, Mamedov, Aliyev, Shomurodov, "
              "Masharipov, Khusanov, Urunov, Sergeev, Ashurmatov, Abdikholikov, Nasrullaev, Alijonov, Hamrobekov, Yusupov, Karimov, "
              "Rakhimov, Tursunov, Nazarov, Kurbanov, Akhmedov, Hajiyev, Mahmudov, Dadashov, Emreli, Sheydayev, Nuriev, Zhukov, "
              "Valiyev, Ibrayev, Satpaev, Zhumabayev, Nurgaliyev, Bekov")),
    "car": (_w("Leon Shamar Bobby Damion Kasey Demarai Michail Ravel Kevin Levi Andre Jamal Dexter Kemar Romario Ricardo Carnejy "
               "Duckens Frantzdy Derrick Mechack Wilde-Donald Bryan Garven Jean-Ricner Danley Kenji Navarone"),
            _l("Bailey, Nicholson, Reid, Antonio, Palmer, Gray, Morrison, Blake, Lowe, Bell, Pinnock, Hector, Latibeaudiere, Leigh, "
               "Moore, Roberts, Phillips, Garcia, Jones, John, Cyrus, Hackshaw, Nazon, Pierrot, Jérôme, Bellegarde, Etienne, Arcus, "
               "Picault, Désir, Duverger, Louicius, Placide, Ade, Lambert, Thompson, Francis, Charles, Williams, Joseph")),
}

REGION = {}
for _r, _codes in {
    "es": "ESP AND", "la": "ARG URU COL CHI PER ECU PAR BOL VEN MEX CRC HON PAN SLV GUA CUB DOM NCA PUR GNQ",
    "br": "BRA", "pt": "POR ANG MOZ CPV GNB STP", "en": "ENG SCO WAL NIR IRL AUS NZL CAN GIB MLT",
    "us": "USA", "fr": "FRA MON", "de": "GER AUT SUI LIE LUX", "it": "ITA SMR", "nl": "NED BEL SUR CUW ARU",
    "yu": "CRO SRB SVN BIH MNE MKD", "ru": "RUS BLR", "ua": "UKR MDA", "pl": "POL", "cz": "CZE SVK", "ro": "ROU",
    "hu": "HUN", "bg": "BUL", "ba": "LVA LTU EST", "cau": "GEO ARM", "al": "ALB KOS",
    "sc": "NOR SWE DEN ISL FIN FRO", "gr": "GRE CYP", "tr": "TUR",
    "ar": "MAR ALG TUN LBY MTN", "gulf": "KSA QAT UAE IRQ JOR SYR LBN KUW BHR OMA YEM PLE EGY SDN",
    "ir": "IRN", "fa": "SEN CIV MLI GUI BFA CMR GAB CGO COD CTA TCH NIG BEN TOG MAD COM DJI BDI RWA",
    "af": "NGA GHA SLE LBR GAM", "afe": "RSA ZAM ZIM KEN TAN UGA MWI BOT NAM LES SWZ ETH SSD ERI SOM",
    "jp": "JPN", "kr": "KOR PRK", "cn": "CHN HKG TPE MAC", "sea": "THA VIE IDN MAS PHI SIN MYA CAM LAO",
    "ca": "KAZ UZB KGZ TJK TKM AZE", "car": "JAM TRI HAI BRB GRN LCA VIN SKN ATG DMA BAH BER CAY",
}.items():
    for _c in _codes.split():
        REGION[_c] = _r
CONF_REGION = {"UEFA": "yu", "CAF": "af", "AFC": "gulf", "CONCACAF": "la", "CONMEBOL": "la", "OFC": "en"}
DOUBLE_SURNAME = {"es": 0.06, "la": 0.05, "pt": 0.08, "br": 0.04}     # иногда две фамилии

def region_of(nat, conf=None):
    return REGION.get(nat) or CONF_REGION.get(conf, "en")

def gen_name(rng, nat, conf):
    r = region_of(nat, conf)
    first, last = NAMES[r]
    sur = rng.choice(last)
    if rng.random() < DOUBLE_SURNAME.get(r, 0.0):
        sur2 = rng.choice(last)
        if sur2 != sur:
            sur = f"{sur} {sur2}"
    return f"{rng.choice(first)} {sur}"
