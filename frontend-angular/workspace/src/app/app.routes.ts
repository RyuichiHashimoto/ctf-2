import { Routes } from '@angular/router';
import { CytoscapePageComponent } from './pages/cytoscape-page.component';
import { MaxGraphPageComponent } from './pages/maxgraph-page.component';

export const appRoutes: Routes = [
  { path: '', redirectTo: 'maxgraph', pathMatch: 'full' },
  { path: 'cytoscape', component: CytoscapePageComponent },
  { path: 'maxgraph', component: MaxGraphPageComponent }
];
