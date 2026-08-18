import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

// Die Root-Komponente stellt nur den Einstiegspunkt für den Router bereit
@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {}
