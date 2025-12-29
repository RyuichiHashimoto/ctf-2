import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { SettingsPanelComponent } from '../components/settings/settings-panel.component';
import { CytoscapeViewComponent } from '../components/contents/cytoscape-view.component';
import { AttackPathService } from '../services/attack-path.service';

@Component({
  selector: 'app-cytoscape-page',
  imports: [CommonModule, SettingsPanelComponent, CytoscapeViewComponent],
  templateUrl: './cytoscape-page.component.html'
})
export class CytoscapePageComponent implements OnInit {
  constructor(public readonly service: AttackPathService) {}

  ngOnInit(): void {
    this.service.loadTactics();
    this.service.connectWebSocket();
  }
}
