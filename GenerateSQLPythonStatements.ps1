$jsonFromScoringSoftware = '{"matchBrief":{"matchName":"Q1","matchNumber":1,"field":1,"red":{"team1":9997,"team2":9996,"isTeam1Surrogate":false,"isTeam2Surrogate":false},"blue":{"team1":9998,"team2":9999,"isTeam1Surrogate":false,"isTeam2Surrogate":false},"finished":true,"matchState":"COMMITTED","time":1635094942317},"startTime":1635092077653,"scheduledTime":-1,"resultPostedTime":1635092279026,"redScore":275,"blueScore":38,"red":{"minorPenalties":0,"majorPenalties":0,"barcodeElement1":"DUCK","barcodeElement2":"DUCK","carousel":false,"autoNavigated1":"IN_WAREHOUSE","autoNavigated2":"COMPLETELY_IN_STORAGE","autoBonus1":true,"autoBonus2":false,"autoStorageFreight":12,"autoFreight1":4,"autoFreight2":6,"autoFreight3":1,"driverControlledStorageFreight":10,"driverControlledFreight1":9,"driverControlledFreight2":6,"driverControlledFreight3":1,"sharedFreight":20,"endgameDelivered":0,"allianceBalanced":false,"sharedUnbalanced":true,"endgameParked1":"NONE","endgameParked2":"COMPLETELY_IN_WAREHOUSE","capped":0,"carouselPoints":0,"autoNavigationPoints":11,"autoFreightPoints":90,"autoBonusPoints":10,"driverControlledAllianceHubPoints":48,"driverControlledSharedHubPoints":80,"driverControlledStoragePoints":10,"endgameDeliveryPoints":0,"allianceBalancedPoints":0,"sharedUnbalancedPoints":20,"endgameParkingPoints":6,"cappingPoints":0,"totalPoints":275,"auto":111,"teleop":138,"end":26,"penalty":0,"dq1":false,"dq2":false},"blue":{"minorPenalties":0,"majorPenalties":0,"barcodeElement1":"DUCK","barcodeElement2":"DUCK","carousel":false,"autoNavigated1":"NONE","autoNavigated2":"NONE","autoBonus1":true,"autoBonus2":false,"autoStorageFreight":2,"autoFreight1":0,"autoFreight2":0,"autoFreight3":4,"driverControlledStorageFreight":0,"driverControlledFreight1":0,"driverControlledFreight2":0,"driverControlledFreight3":0,"sharedFreight":0,"endgameDelivered":0,"allianceBalanced":false,"sharedUnbalanced":false,"endgameParked1":"NONE","endgameParked2":"NONE","capped":0,"carouselPoints":0,"autoNavigationPoints":0,"autoFreightPoints":28,"autoBonusPoints":10,"driverControlledAllianceHubPoints":0,"driverControlledSharedHubPoints":0,"driverControlledStoragePoints":0,"endgameDeliveryPoints":0,"allianceBalancedPoints":0,"sharedUnbalancedPoints":0,"endgameParkingPoints":0,"cappingPoints":0,"totalPoints":38,"auto":38,"teleop":0,"end":0,"penalty":0,"dq1":false,"dq2":false},"randomization":2}'
$jsonFromScoringSoftware = $jsonFromScoringSoftware | ConvertFrom-Json


$PYTHON_Output = @()
$SQL_OUTPUT = @()

foreach($property in ($jsonFromScoringSoftware.PSObject.Properties)){
    if($property.Value.GetType().Name -eq "PSCustomObject"){


        foreach($element in $property.Value.PSObject.Properties){

            if($element.Value.GetType().Name -eq "PSCustomObject"){
                
                foreach($subElement in $element.Value.PSObject.Properties){
                   $PYTHON_Output += "matchResults[`"$($property.Name)`"][`"$($element.Name)`"][`"$($subElement.Name)`"]"
                   $SQL_OUTPUT += "``$($property.Name)_$($element.Name)_$($subElement.Name)``"

                }
            }else{
                $PYTHON_Output +=  "matchResults[`"$($property.Name)`"][`"$($element.Name)`"]"
                $SQL_OUTPUT += "``$($property.Name)_$($element.Name)``"
            }
        }
    }else{
        $PYTHON_Output +=  "matchResults[`"$($property.Name)`"]"
        $SQL_OUTPUT += "``$($property.Name)``"
    }
}


Write-Host "==========SQL Schema START=========="
foreach($item in $SQL_OUTPUT){
    Write-Host $item
}
Write-Host "==========SQL Schema END=========="

Write-Host "==========SQL INSERT START=========="
$columns = "``eventCode``, "
$columns += $SQL_OUTPUT -join ", "


$sql_values = @()
foreach($item in $SQL_OUTPUT){
    if($item -match "time"){
        $sql_values += "FROM_UNIXTIME(%s)"
    }else{
        $sql_values += "%s"
    }
}

$sql_values = $sql_values -join ", "

Write-Host "INSERT INTO {table_name} ($($columns)) VALUES (%s, $($sql_values));"

Write-Host "==========SQL INSERT END=========="


Write-Host "==========SQL UPDATE START=========="

$sql_setfield = @()
foreach($item in $SQL_OUTPUT){
    if($item -match "time"){
        $sql_setfield += "$($item)=FROM_UNIXTIME(%s)"
    }else{
        $sql_setfield += "$($item)=%s"
    }
}

$sql_setfield = $sql_setfield -join ", "

Write-Host "UPDATE {table_name} SET $($sql_setfield) WHERE `eventCode` = %s AND matchBrief_matchNumber = %s;"

Write-Host "==========SQL UPDATE END=========="

Write-Host "==========PYTHON UPDATE START=========="

$output = @()

foreach($item in $PYTHON_Output){
    if($item -match "time"){
        $output += "max(1, ($($item))/1000)"
    }else{
        $output += $item
    }
}

$output = $output -join ", "
$output + ', self.eventCode, matchResults["matchBrief"]["matchNumber"]'

Write-Host "==========PYTHON UPDATE END=========="


Write-Host "==========PYTHON INSERT START=========="
$output = @()
$output += "self.eventCode"

foreach($item in $PYTHON_Output){
    if($item -match "time"){
        $output += "max(1, ($($item)/1000))"
    }else{
        $output += $item
    }
}

$output = $output -join ", "
$output

Write-Host "==========PYTHON INSERT END=========="
