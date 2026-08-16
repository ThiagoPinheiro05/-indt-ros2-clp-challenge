PROGRAM turtle_motor_control
  VAR
    CmdLinearRaw AT %IW100 : INT;
    CmdAngularRaw AT %IW101 : INT;
    HeartbeatIW AT %IW104 : INT;

    MotorSpeedPercent AT %MW10 : INT;
    MotorEnable AT %MW11 : INT;
    MotorDirectionFwd AT %MW12 : INT;
    WatchdogFault AT %MW13 : INT;

    SpeedOut AT %QW100 : INT;
    EnableOut AT %QW101 : INT;
    DirectionOut AT %QW102 : INT;
  END_VAR

  VAR
    FirstScan : BOOL := TRUE;
    LastHeartbeat : INT;
    HeartbeatChanged : BOOL;
    WatchdogTimer : TON;
    WatchdogFaultBool : BOOL;

    LinearAbs : INT;
    DeadZoneThreshold : INT := 5;
    TargetPercent : INT;
    RampStep : INT := 3;
  END_VAR

  IF FirstScan THEN
    LastHeartbeat := HeartbeatIW;
    FirstScan := FALSE;
    HeartbeatChanged := TRUE;
  ELSIF HeartbeatIW <> LastHeartbeat THEN
    HeartbeatChanged := TRUE;
    LastHeartbeat := HeartbeatIW;
  ELSE
    HeartbeatChanged := FALSE;
  END_IF;

  WatchdogTimer(IN := NOT HeartbeatChanged, PT := T#1s);
  WatchdogFaultBool := WatchdogTimer.Q;

  IF WatchdogFaultBool THEN
    WatchdogFault := 1;
  ELSE
    WatchdogFault := 0;
  END_IF;

  LinearAbs := ABS(CmdLinearRaw);

  IF LinearAbs < DeadZoneThreshold THEN
    LinearAbs := 0;
  END_IF;

  TargetPercent := LinearAbs / 2;

  IF TargetPercent > 100 THEN
    TargetPercent := 100;
  END_IF;

  IF WatchdogFaultBool THEN
    TargetPercent := 0;
  END_IF;

  IF TargetPercent < MotorSpeedPercent THEN
    MotorSpeedPercent := TargetPercent;
  ELSIF TargetPercent > MotorSpeedPercent THEN
    MotorSpeedPercent := MotorSpeedPercent + RampStep;
    IF MotorSpeedPercent > TargetPercent THEN
      MotorSpeedPercent := TargetPercent;
    END_IF;
  END_IF;

  IF CmdLinearRaw >= 0 THEN
    MotorDirectionFwd := 1;
  ELSE
    MotorDirectionFwd := 0;
  END_IF;

  IF MotorSpeedPercent > 0 THEN
    MotorEnable := 1;
  ELSE
    MotorEnable := 0;
  END_IF;

  SpeedOut := MotorSpeedPercent;
  EnableOut := MotorEnable;
  DirectionOut := MotorDirectionFwd;

END_PROGRAM

CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    TASK task0(INTERVAL := T#20ms, PRIORITY := 0);
    PROGRAM instance0 WITH task0 : turtle_motor_control;
  END_RESOURCE
END_CONFIGURATION
